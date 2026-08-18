"""Enrollment (effectifs) analytics for the Préfet BI module."""

from __future__ import annotations

from typing import Any

from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.bi.constants import occupancy_status
from apps.bi.filters import BiFilters
from apps.bi.selectors.enrollment_selectors import (
    classes_with_occupancy,
    validated_enrollments_qs,
)
from apps.secretariat.models import AcademicYear, Enrollment, Student


def build_enrollment_analytics(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> dict[str, Any]:
    filters = filters or BiFilters()
    qs = validated_enrollments_qs(academic_year, filters)

    effectif_total = qs.count()
    nouvelles = qs.filter(enrollment_type=Enrollment.EnrollmentType.NEW).count()
    reinscriptions = qs.filter(enrollment_type=Enrollment.EnrollmentType.RENEWAL).count()
    transferts = qs.filter(
        enrollment_type=Enrollment.EnrollmentType.INCOMING_TRANSFER
    ).count()

    by_gender = {
        row["student__sexe"]: row["c"]
        for row in qs.values("student__sexe").annotate(c=Count("id"))
    }
    garcons = by_gender.get(Student.Gender.MALE, 0)
    filles = by_gender.get(Student.Gender.FEMALE, 0)
    autres = by_gender.get(Student.Gender.OTHER, 0)

    by_level = list(
        qs.values("school_class__level__name", "school_class__level__order")
        .annotate(effectif=Count("id"))
        .order_by("school_class__level__order", "school_class__level__name")
    )
    by_section = list(
        qs.values("school_class__section__name")
        .annotate(effectif=Count("id"))
        .order_by("school_class__section__name")
    )
    by_option = list(
        qs.values("school_class__option__name")
        .annotate(effectif=Count("id"))
        .order_by("school_class__option__name")
    )
    by_class = list(
        qs.values("school_class_id", "school_class__name")
        .annotate(effectif=Count("id"))
        .order_by("school_class__name")
    )

    monthly = list(
        qs.annotate(period=TruncMonth("enrollment_date"))
        .values("period")
        .annotate(effectif=Count("id"))
        .order_by("period")
    )
    trend_labels = [
        row["period"].strftime("%Y-%m") if row["period"] else ""
        for row in monthly
    ]
    trend_values = [row["effectif"] for row in monthly]

    occupancy_rows: list[dict[str, Any]] = []
    for school_class in classes_with_occupancy(academic_year, filters):
        capacity = school_class.max_capacity or 0
        occupied = school_class.occupied or 0
        rate = round(occupied * 100 / capacity, 1) if capacity else None
        remaining = max(capacity - occupied, 0) if capacity else None
        occupancy_rows.append(
            {
                "class_id": school_class.pk,
                "name": school_class.name,
                "level": school_class.level.name if school_class.level_id else "",
                "capacity": capacity,
                "effectif": occupied,
                "places_restantes": remaining,
                "taux_occupation": rate,
                "statut": occupancy_status(occupied=occupied, capacity=capacity),
            }
        )

    return {
        "kpis": {
            "effectif_total": effectif_total,
            "nouvelles_inscriptions": nouvelles,
            "reinscriptions": reinscriptions,
            "transferts_entrants": transferts,
            "garcons": garcons,
            "filles": filles,
            "autres": autres,
            "classes_actives": classes_with_occupancy(academic_year, filters).count(),
        },
        "charts": {
            "trend": {
                "labels": trend_labels,
                "series": [{"name": "Inscriptions validées", "data": trend_values}],
            },
            "by_class": {
                "labels": [r["school_class__name"] for r in by_class],
                "series": [
                    {
                        "name": "Effectif",
                        "data": [r["effectif"] for r in by_class],
                    }
                ],
            },
            "by_gender": {
                "labels": ["Garçons", "Filles", "Autres"],
                "series": [
                    {
                        "name": "Répartition",
                        "data": [garcons, filles, autres],
                    }
                ],
            },
            "by_level": {
                "labels": [r["school_class__level__name"] or "—" for r in by_level],
                "series": [
                    {
                        "name": "Effectif",
                        "data": [r["effectif"] for r in by_level],
                    }
                ],
            },
        },
        "tables": {
            "by_class": by_class,
            "by_level": by_level,
            "by_section": by_section,
            "by_option": by_option,
            "occupation": occupancy_rows,
        },
        "filters": filters.as_dict(),
        "generated_at": timezone.now(),
    }
