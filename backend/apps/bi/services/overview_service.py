"""BI executive overview KPIs and alerts for a selected academic year."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.bi.constants import (
    LOW_COLLECTION_THRESHOLD,
    MONEY,
    OPEN_INCIDENT_STATUSES,
    PENDING_SUMMONS_STATUSES,
    PRESENT_LIKE,
    SEVERE_SEVERITIES,
    ZERO,
)
from apps.bi.selectors.attendance_selectors import attendance_qs
from apps.bi.selectors.discipline_selectors import incidents_qs, summons_qs
from apps.bi.selectors.enrollment_selectors import (
    classes_with_occupancy,
    validated_enrollments_qs,
)
from apps.bi.selectors.financial_selectors import obligations_qs, valid_payments_qs
from apps.discipline.models import DailyAttendance
from apps.secretariat.models import AcademicYear


def build_overview(academic_year: AcademicYear) -> dict[str, Any]:
    """Aggregate cross-module KPIs and attention alerts for the Préfet."""
    effectif_total = validated_enrollments_qs(academic_year).count()

    classes_annotated = classes_with_occupancy(academic_year)
    classes_actives = classes_annotated.count()

    occupation_rates: list[float] = []
    capacity_alerts: list[dict[str, str]] = []
    for school_class in classes_annotated:
        capacity = school_class.max_capacity or 0
        occupied = school_class.occupied or 0
        if capacity > 0:
            occupation_rates.append(round(occupied * 100 / capacity, 1))
        if capacity > 0 and occupied > capacity:
            capacity_alerts.append(
                {
                    "level": "danger",
                    "title": "Capacité dépassée",
                    "detail": (
                        f"{school_class.name} : {occupied} élèves pour "
                        f"{capacity} places."
                    ),
                }
            )

    occupation_moyenne: float | None = None
    if occupation_rates:
        occupation_moyenne = round(sum(occupation_rates) / len(occupation_rates), 1)

    obligation_agg = obligations_qs(academic_year).aggregate(
        total_due=Coalesce(Sum("amount_due"), Value(ZERO), output_field=MONEY),
    )
    montant_attendu = Decimal(obligation_agg["total_due"] or ZERO)

    # Paiements ANNULE exclus : status=VALIDE uniquement.
    payments_agg = valid_payments_qs(academic_year).aggregate(
        total_collected=Coalesce(Sum("amount_total"), Value(ZERO), output_field=MONEY),
    )
    montant_encaisse = Decimal(payments_agg["total_collected"] or ZERO)

    solde = montant_attendu - montant_encaisse
    if solde < ZERO:
        solde = ZERO

    taux_recouvrement: Decimal | None = None
    if montant_attendu > ZERO:
        taux_recouvrement = (montant_encaisse * Decimal("100") / montant_attendu).quantize(
            Decimal("0.1")
        )

    attendance_agg = attendance_qs(academic_year).aggregate(
        total=Count("id"),
        present_like=Count("id", filter=Q(status__in=PRESENT_LIKE)),
        late=Count("id", filter=Q(status=DailyAttendance.Status.LATE)),
    )
    attendance_total = attendance_agg["total"] or 0
    present_like = attendance_agg["present_like"] or 0
    retards = attendance_agg["late"] or 0

    taux_presence: float | None = None
    if attendance_total > 0:
        taux_presence = round(present_like * 100 / attendance_total, 1)

    incidents_ouverts = incidents_qs(academic_year).filter(
        status__in=OPEN_INCIDENT_STATUSES,
    ).count()

    convocations_attente = summons_qs(academic_year).filter(
        status__in=PENDING_SUMMONS_STATUSES,
    ).count()

    alerts: list[dict[str, str]] = list(capacity_alerts)

    if (
        taux_recouvrement is not None
        and montant_attendu > ZERO
        and taux_recouvrement < LOW_COLLECTION_THRESHOLD
    ):
        alerts.append(
            {
                "level": "warning",
                "title": "Recouvrement faible",
                "detail": (
                    f"Taux de recouvrement à {taux_recouvrement} % "
                    f"(seuil {LOW_COLLECTION_THRESHOLD} %)."
                ),
            }
        )

    severe_open = incidents_qs(academic_year).filter(
        status__in=OPEN_INCIDENT_STATUSES,
        severity__in=SEVERE_SEVERITIES,
    ).count()
    if severe_open:
        alerts.append(
            {
                "level": "danger",
                "title": "Incidents graves ouverts",
                "detail": (
                    f"{severe_open} incident(s) grave(s) ou très grave(s) "
                    "encore ouvert(s)."
                ),
            }
        )

    return {
        "kpis": {
            "effectif_total": effectif_total,
            "classes_actives": classes_actives,
            "occupation_moyenne": occupation_moyenne,
            "montant_attendu": montant_attendu,
            "montant_encaisse": montant_encaisse,
            "solde": solde,
            "taux_recouvrement": taux_recouvrement,
            "taux_presence": taux_presence,
            "retards": retards,
            "incidents_ouverts": incidents_ouverts,
            "convocations_attente": convocations_attente,
        },
        "alerts": alerts,
        "generated_at": timezone.now(),
    }
