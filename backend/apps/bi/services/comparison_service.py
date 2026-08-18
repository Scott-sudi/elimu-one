"""Cross-year comparison analytics for the Préfet BI module."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.bi.constants import MONEY, OPEN_INCIDENT_STATUSES, PRESENT_LIKE, ZERO
from apps.bi.selectors.attendance_selectors import attendance_qs
from apps.bi.selectors.discipline_selectors import incidents_qs
from apps.bi.selectors.enrollment_selectors import (
    classes_with_occupancy,
    validated_enrollments_qs,
)
from apps.bi.selectors.financial_selectors import obligations_qs, valid_payments_qs
from apps.discipline.models import DailyAttendance
from apps.secretariat.models import AcademicYear


def _year_snapshot(year: AcademicYear) -> dict[str, Any]:
    effectif = validated_enrollments_qs(year).count()
    classes = classes_with_occupancy(year)
    classes_actives = classes.count()
    rates = []
    for school_class in classes:
        capacity = school_class.max_capacity or 0
        occupied = school_class.occupied or 0
        if capacity > 0:
            rates.append(occupied * 100 / capacity)
    occupation = round(sum(rates) / len(rates), 1) if rates else None

    attendu = Decimal(
        obligations_qs(year).aggregate(
            t=Coalesce(Sum("amount_due"), Value(ZERO), output_field=MONEY)
        )["t"]
        or ZERO
    )
    encaisse = Decimal(
        valid_payments_qs(year).aggregate(
            t=Coalesce(Sum("amount_total"), Value(ZERO), output_field=MONEY)
        )["t"]
        or ZERO
    )
    recovery = None
    if attendu > ZERO:
        recovery = (encaisse * Decimal("100") / attendu).quantize(Decimal("0.1"))

    att = attendance_qs(year).aggregate(
        total=Count("id"),
        present_like=Count("id", filter=Q(status__in=PRESENT_LIKE)),
        late=Count("id", filter=Q(status=DailyAttendance.Status.LATE)),
    )
    att_total = att["total"] or 0
    presence = (
        round(att["present_like"] * 100 / att_total, 1) if att_total else None
    )
    incidents_ouverts = incidents_qs(year).filter(
        status__in=OPEN_INCIDENT_STATUSES
    ).count()

    return {
        "year_id": year.pk,
        "label": year.label,
        "is_active": year.is_active,
        "is_closed": year.is_closed,
        "effectif_total": effectif,
        "classes_actives": classes_actives,
        "occupation_moyenne": occupation,
        "montant_attendu": attendu,
        "montant_encaisse": encaisse,
        "taux_recouvrement": recovery,
        "taux_presence": presence,
        "retards": att["late"] or 0,
        "incidents_ouverts": incidents_ouverts,
    }


def build_year_comparison(
    *,
    year_ids: list[int] | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Compare KPIs across academic years (explicit comparison page only)."""
    qs = AcademicYear.objects.all().order_by("start_date")
    if year_ids:
        qs = qs.filter(pk__in=year_ids)
    else:
        qs = qs.order_by("-start_date")[:limit]
        qs = sorted(qs, key=lambda y: y.start_date)

    snapshots = [_year_snapshot(year) for year in qs]
    labels = [s["label"] for s in snapshots]

    return {
        "kpis": {
            "annees_comparees": len(snapshots),
        },
        "charts": {
            "years": {
                "labels": labels,
                "series": [
                    {
                        "name": "Effectif",
                        "data": [s["effectif_total"] for s in snapshots],
                    },
                    {
                        "name": "Classes actives",
                        "data": [s["classes_actives"] for s in snapshots],
                    },
                ],
            },
            "kpis": {
                "labels": labels,
                "series": [
                    {
                        "name": "Taux de recouvrement (%)",
                        "data": [
                            float(s["taux_recouvrement"])
                            if s["taux_recouvrement"] is not None
                            else 0
                            for s in snapshots
                        ],
                    },
                    {
                        "name": "Taux de présence (%)",
                        "data": [
                            s["taux_presence"] if s["taux_presence"] is not None else 0
                            for s in snapshots
                        ],
                    },
                    {
                        "name": "Occupation moyenne (%)",
                        "data": [
                            s["occupation_moyenne"]
                            if s["occupation_moyenne"] is not None
                            else 0
                            for s in snapshots
                        ],
                    },
                ],
            },
        },
        "tables": {
            "years": snapshots,
        },
        "generated_at": timezone.now(),
    }
