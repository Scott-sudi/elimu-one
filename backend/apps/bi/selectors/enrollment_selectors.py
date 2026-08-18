"""Enrollment / effectifs querysets for BI."""

from __future__ import annotations

from django.db.models import Count, Q, QuerySet

from apps.bi.filters import BiFilters, apply_class_structure_filters, apply_date_range
from apps.secretariat.models import AcademicYear, Enrollment, SchoolClass


def enrollments_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> QuerySet[Enrollment]:
    qs = Enrollment.objects.filter(academic_year=academic_year).select_related(
        "student",
        "school_class",
        "school_class__level",
        "school_class__section",
        "school_class__option",
    )
    filters = filters or BiFilters()
    qs = apply_class_structure_filters(qs, filters)
    qs = apply_date_range(qs, filters, field="enrollment_date")
    if filters.enrollment_status:
        qs = qs.filter(status=filters.enrollment_status)
    if filters.enrollment_type:
        qs = qs.filter(enrollment_type=filters.enrollment_type)
    if filters.gender:
        qs = qs.filter(student__sexe=filters.gender)
    return qs


def validated_enrollments_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> QuerySet[Enrollment]:
    filters = filters or BiFilters()
    if not filters.enrollment_status:
        filters = BiFilters(
            **{**filters.__dict__, "enrollment_status": Enrollment.Status.VALIDATED}
        )
    return enrollments_qs(academic_year, filters)


def active_classes_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> QuerySet[SchoolClass]:
    qs = SchoolClass.objects.filter(
        academic_year=academic_year,
        is_active=True,
    ).select_related("level", "section", "option")
    filters = filters or BiFilters()
    if filters.class_id:
        qs = qs.filter(pk=filters.class_id)
    if filters.level_id:
        qs = qs.filter(level_id=filters.level_id)
    if filters.section_id:
        qs = qs.filter(section_id=filters.section_id)
    if filters.option_id:
        qs = qs.filter(option_id=filters.option_id)
    return qs


def classes_with_occupancy(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> QuerySet[SchoolClass]:
    return active_classes_qs(academic_year, filters).annotate(
        occupied=Count(
            "enrollments",
            filter=Q(enrollments__status=Enrollment.Status.VALIDATED),
        ),
    )
