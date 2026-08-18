"""Financial analytics for the Préfet BI module."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from apps.bi.constants import MONEY, ZERO
from apps.bi.filters import BiFilters
from apps.bi.selectors.financial_selectors import (
    cancelled_payments_qs,
    obligations_qs,
    valid_payments_qs,
)
from apps.finance.models import Payment, StudentFeeObligation
from apps.secretariat.models import AcademicYear, Enrollment


def _rate(collected: Decimal, expected: Decimal) -> Decimal | None:
    if expected <= ZERO:
        return None
    return (collected * Decimal("100") / expected).quantize(Decimal("0.1"))


def build_financial_analytics(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> dict[str, Any]:
    filters = filters or BiFilters()
    today = timezone.localdate()

    obligations = obligations_qs(academic_year, filters)
    obligation_agg = obligations.aggregate(
        total_due=Coalesce(Sum("amount_due"), Value(ZERO), output_field=MONEY),
        total_paid_on_ob=Coalesce(Sum("amount_paid"), Value(ZERO), output_field=MONEY),
    )
    montant_attendu = Decimal(obligation_agg["total_due"] or ZERO)

    payments = valid_payments_qs(academic_year, filters)
    payments_agg = payments.aggregate(
        total_collected=Coalesce(Sum("amount_total"), Value(ZERO), output_field=MONEY),
        receipt_count=Count("id"),
    )
    # ANNULE exclus via valid_payments_qs (status=VALIDE).
    montant_encaisse = Decimal(payments_agg["total_collected"] or ZERO)
    solde = montant_attendu - montant_encaisse
    if solde < ZERO:
        solde = ZERO
    taux_recouvrement = _rate(montant_encaisse, montant_attendu)

    encaisse_jour = Decimal(
        payments.filter(payment_date=today).aggregate(
            t=Coalesce(Sum("amount_total"), Value(ZERO), output_field=MONEY)
        )["t"]
        or ZERO
    )
    encaisse_mois = Decimal(
        payments.filter(
            payment_date__year=today.year,
            payment_date__month=today.month,
        ).aggregate(
            t=Coalesce(Sum("amount_total"), Value(ZERO), output_field=MONEY)
        )["t"]
        or ZERO
    )

    cancelled_count = cancelled_payments_qs(academic_year, filters).count()
    receipts = payments_agg["receipt_count"] or 0

    # Élèves (inscriptions validées) selon situation d'obligations.
    enrollment_ids = (
        Enrollment.objects.filter(
            academic_year=academic_year,
            status=Enrollment.Status.VALIDATED,
        )
        .values_list("id", flat=True)
    )
    if filters.class_id or filters.level_id or filters.section_id or filters.option_id:
        from apps.bi.filters import apply_class_structure_filters

        e_qs = Enrollment.objects.filter(
            academic_year=academic_year,
            status=Enrollment.Status.VALIDATED,
        )
        e_qs = apply_class_structure_filters(e_qs, filters)
        enrollment_ids = e_qs.values_list("id", flat=True)

    enrollment_ids = list(enrollment_ids)
    ob_by_enrollment = (
        obligations_qs(academic_year, filters)
        .filter(enrollment_id__in=enrollment_ids)
        .values("enrollment_id")
        .annotate(
            due=Coalesce(Sum("amount_due"), Value(ZERO), output_field=MONEY),
            paid=Coalesce(Sum("amount_paid"), Value(ZERO), output_field=MONEY),
            unpaid_flags=Count(
                "id",
                filter=Q(status=StudentFeeObligation.Status.UNPAID),
            ),
            partial_flags=Count(
                "id",
                filter=Q(status=StudentFeeObligation.Status.PARTIAL),
            ),
        )
    )
    eleves_en_ordre = 0
    eleves_partiels = 0
    eleves_sans_paiement = 0
    for row in ob_by_enrollment:
        due = Decimal(row["due"] or ZERO)
        paid = Decimal(row["paid"] or ZERO)
        if due <= ZERO or paid >= due:
            eleves_en_ordre += 1
        elif paid <= ZERO:
            eleves_sans_paiement += 1
        else:
            eleves_partiels += 1

    monthly = list(
        payments.annotate(period=TruncMonth("payment_date"))
        .values("period")
        .annotate(
            montant=Coalesce(Sum("amount_total"), Value(ZERO), output_field=MONEY)
        )
        .order_by("period")
    )

    by_class = list(
        payments.values(
            "enrollment__school_class_id",
            "enrollment__school_class__name",
        )
        .annotate(
            montant_encaisse=Coalesce(
                Sum("amount_total"), Value(ZERO), output_field=MONEY
            ),
            nb_paiements=Count("id"),
        )
        .order_by("enrollment__school_class__name")
    )

    by_fee = list(
        obligations.values("fee_id", "fee__code", "fee__label")
        .annotate(
            montant_attendu=Coalesce(Sum("amount_due"), Value(ZERO), output_field=MONEY),
            montant_paye_ob=Coalesce(Sum("amount_paid"), Value(ZERO), output_field=MONEY),
        )
        .order_by("fee__label")
    )
    fee_rows = []
    for row in by_fee:
        attendu = Decimal(row["montant_attendu"] or ZERO)
        paye = Decimal(row["montant_paye_ob"] or ZERO)
        fee_rows.append(
            {
                "fee_id": row["fee_id"],
                "code": row["fee__code"],
                "label": row["fee__label"],
                "montant_attendu": attendu,
                "montant_paye": paye,
                "solde": max(attendu - paye, ZERO),
                "taux_recouvrement": _rate(paye, attendu),
            }
        )

    by_method = list(
        payments.values("payment_method")
        .annotate(
            montant=Coalesce(Sum("amount_total"), Value(ZERO), output_field=MONEY),
            nb=Count("id"),
        )
        .order_by("payment_method")
    )
    method_labels = {
        code: label for code, label in Payment.PaymentMethod.choices
    }

    expected_by_class = {
        row["enrollment__school_class_id"]: Decimal(row["due"] or ZERO)
        for row in obligations.values("enrollment__school_class_id").annotate(
            due=Coalesce(Sum("amount_due"), Value(ZERO), output_field=MONEY)
        )
    }
    class_comparison = []
    for row in by_class:
        class_id = row["enrollment__school_class_id"]
        encaisse = Decimal(row["montant_encaisse"] or ZERO)
        attendu = expected_by_class.get(class_id, ZERO)
        class_comparison.append(
            {
                "class_id": class_id,
                "name": row["enrollment__school_class__name"],
                "montant_attendu": attendu,
                "montant_encaisse": encaisse,
                "solde": max(attendu - encaisse, ZERO),
                "taux_recouvrement": _rate(encaisse, attendu),
                "nb_paiements": row["nb_paiements"],
            }
        )

    return {
        "kpis": {
            "montant_attendu": montant_attendu,
            "montant_encaisse": montant_encaisse,
            "solde": solde,
            "taux_recouvrement": taux_recouvrement,
            "encaisse_jour": encaisse_jour,
            "encaisse_mois": encaisse_mois,
            "eleves_en_ordre": eleves_en_ordre,
            "eleves_partiels": eleves_partiels,
            "eleves_sans_paiement": eleves_sans_paiement,
            "paiements_annules": cancelled_count,
            "nombre_recus": receipts,
        },
        "charts": {
            "collections": {
                "labels": [
                    row["period"].strftime("%Y-%m") if row["period"] else ""
                    for row in monthly
                ],
                "series": [
                    {
                        "name": "Encaissements (VALIDE)",
                        "data": [str(row["montant"]) for row in monthly],
                    }
                ],
            },
            "by_class": {
                "labels": [r["name"] for r in class_comparison],
                "series": [
                    {
                        "name": "Attendu",
                        "data": [str(r["montant_attendu"]) for r in class_comparison],
                    },
                    {
                        "name": "Encaissé",
                        "data": [str(r["montant_encaisse"]) for r in class_comparison],
                    },
                    {
                        "name": "Solde",
                        "data": [str(r["solde"]) for r in class_comparison],
                    },
                ],
            },
            "by_method": {
                "labels": [
                    method_labels.get(r["payment_method"], r["payment_method"])
                    for r in by_method
                ],
                "series": [
                    {
                        "name": "Montant",
                        "data": [str(r["montant"]) for r in by_method],
                    }
                ],
            },
            "recovery": {
                "labels": [r["label"] for r in fee_rows],
                "series": [
                    {
                        "name": "Taux de recouvrement (%)",
                        "data": [
                            float(r["taux_recouvrement"])
                            if r["taux_recouvrement"] is not None
                            else 0
                            for r in fee_rows
                        ],
                    }
                ],
            },
        },
        "tables": {
            "by_class": class_comparison,
            "by_fee": fee_rows,
            "by_method": [
                {
                    "method": r["payment_method"],
                    "label": method_labels.get(r["payment_method"], r["payment_method"]),
                    "montant": r["montant"],
                    "nb": r["nb"],
                }
                for r in by_method
            ],
        },
        "filters": filters.as_dict(),
        "generated_at": timezone.now(),
    }
