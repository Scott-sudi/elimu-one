"""Discipline analytics for the Préfet BI module."""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.bi.constants import (
    CLOSED_INCIDENT_STATUSES,
    OPEN_INCIDENT_STATUSES,
    PENDING_SUMMONS_STATUSES,
)
from apps.bi.filters import BiFilters
from apps.bi.selectors.discipline_selectors import incidents_qs, measures_qs, summons_qs
from apps.discipline.models import DisciplinaryIncident, ParentSummons
from apps.secretariat.models import AcademicYear


def build_discipline_analytics(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> dict[str, Any]:
    filters = filters or BiFilters()
    incidents = incidents_qs(academic_year, filters)
    measures = measures_qs(academic_year, filters)
    summons = summons_qs(academic_year, filters)

    total = incidents.count()
    ouverts = incidents.filter(status__in=OPEN_INCIDENT_STATUSES).count()
    clotures = incidents.filter(status__in=CLOSED_INCIDENT_STATUSES).count()

    by_severity = list(
        incidents.values("severity").annotate(nb=Count("id")).order_by("severity")
    )
    severity_labels = dict(DisciplinaryIncident.Severity.choices)

    by_category = list(
        incidents.values("category_id", "category__name", "category__observation_type")
        .annotate(nb=Count("id"))
        .order_by("-nb", "category__name")
    )

    positives = incidents.filter(
        category__observation_type="POSITIVE"
    ).count()

    monthly = list(
        incidents.annotate(period=TruncMonth("incident_date"))
        .values("period")
        .annotate(nb=Count("id"))
        .order_by("period")
    )

    by_class = list(
        incidents.values("school_class_id", "school_class__name")
        .annotate(
            total=Count("id"),
            ouverts=Count("id", filter=Q(status__in=OPEN_INCIDENT_STATUSES)),
        )
        .order_by("-total", "school_class__name")
    )

    recidives = list(
        incidents.values(
            "student_id",
            "student__matricule",
            "student__nom",
            "student__prenom",
            "school_class__name",
        )
        .annotate(nb=Count("id"))
        .filter(nb__gte=2)
        .order_by("-nb")[:50]
    )

    summons_agg = summons.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status__in=PENDING_SUMMONS_STATUSES)),
        present=Count("id", filter=Q(status=ParentSummons.Status.PRESENT)),
        absent=Count("id", filter=Q(status=ParentSummons.Status.ABSENT)),
    )
    by_summons_status = list(
        summons.values("status").annotate(nb=Count("id")).order_by("status")
    )
    summons_labels = dict(ParentSummons.Status.choices)

    measures_count = measures.count()
    by_measure = list(
        measures.values("measure_type__name")
        .annotate(nb=Count("id"))
        .order_by("-nb")
    )

    return {
        "kpis": {
            "incidents_total": total,
            "incidents_ouverts": ouverts,
            "incidents_clotures": clotures,
            "mesures": measures_count,
            "convocations": summons_agg["total"] or 0,
            "convocations_attente": summons_agg["pending"] or 0,
            "responsables_presents": summons_agg["present"] or 0,
            "responsables_absents": summons_agg["absent"] or 0,
            "observations_positives": positives,
            "recidives": len(recidives),
        },
        "charts": {
            "severity": {
                "labels": [
                    severity_labels.get(r["severity"], r["severity"])
                    for r in by_severity
                ],
                "series": [{"name": "Incidents", "data": [r["nb"] for r in by_severity]}],
            },
            "summons": {
                "labels": [
                    summons_labels.get(r["status"], r["status"])
                    for r in by_summons_status
                ],
                "series": [
                    {"name": "Convocations", "data": [r["nb"] for r in by_summons_status]}
                ],
            },
            "trend": {
                "labels": [
                    row["period"].strftime("%Y-%m") if row["period"] else ""
                    for row in monthly
                ],
                "series": [{"name": "Incidents", "data": [row["nb"] for row in monthly]}],
            },
            "by_class": {
                "labels": [r["school_class__name"] for r in by_class],
                "series": [
                    {"name": "Incidents", "data": [r["total"] for r in by_class]}
                ],
            },
            "by_category": {
                "labels": [r["category__name"] for r in by_category],
                "series": [{"name": "Incidents", "data": [r["nb"] for r in by_category]}],
            },
        },
        "tables": {
            "by_class": by_class,
            "by_category": by_category,
            "by_severity": [
                {
                    "severity": r["severity"],
                    "label": severity_labels.get(r["severity"], r["severity"]),
                    "nb": r["nb"],
                }
                for r in by_severity
            ],
            "recidives": recidives,
            "measures": by_measure,
            "summons": [
                {
                    "status": r["status"],
                    "label": summons_labels.get(r["status"], r["status"]),
                    "nb": r["nb"],
                }
                for r in by_summons_status
            ],
        },
        "filters": filters.as_dict(),
        "generated_at": timezone.now(),
    }
