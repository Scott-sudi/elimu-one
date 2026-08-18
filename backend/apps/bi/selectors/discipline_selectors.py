"""Discipline querysets for BI."""

from __future__ import annotations

from django.db.models import QuerySet

from apps.bi.filters import BiFilters, apply_class_structure_filters, apply_date_range
from apps.discipline.models import DisciplinaryIncident, DisciplinaryMeasure, ParentSummons
from apps.secretariat.models import AcademicYear


def incidents_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
    *,
    include_archived: bool = False,
) -> QuerySet[DisciplinaryIncident]:
    qs = DisciplinaryIncident.objects.filter(academic_year=academic_year).select_related(
        "student",
        "school_class",
        "category",
    )
    if not include_archived:
        qs = qs.filter(is_archived=False)
    filters = filters or BiFilters()
    qs = apply_class_structure_filters(qs, filters)
    qs = apply_date_range(qs, filters, field="incident_date")
    if filters.incident_severity:
        qs = qs.filter(severity=filters.incident_severity)
    if filters.incident_status:
        qs = qs.filter(status=filters.incident_status)
    if filters.category_id:
        qs = qs.filter(category_id=filters.category_id)
    if filters.gender:
        qs = qs.filter(student__sexe=filters.gender)
    return qs


def measures_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> QuerySet[DisciplinaryMeasure]:
    qs = DisciplinaryMeasure.objects.filter(
        incident__academic_year=academic_year,
        is_cancelled=False,
    ).select_related("student", "measure_type", "incident")
    filters = filters or BiFilters()
    if filters.class_id:
        qs = qs.filter(incident__school_class_id=filters.class_id)
    if filters.level_id:
        qs = qs.filter(incident__school_class__level_id=filters.level_id)
    if filters.section_id:
        qs = qs.filter(incident__school_class__section_id=filters.section_id)
    if filters.option_id:
        qs = qs.filter(incident__school_class__option_id=filters.option_id)
    if filters.gender:
        qs = qs.filter(student__sexe=filters.gender)
    return qs


def summons_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> QuerySet[ParentSummons]:
    qs = ParentSummons.objects.filter(academic_year=academic_year).select_related(
        "student",
        "incident",
        "incident__school_class",
    )
    filters = filters or BiFilters()
    if filters.class_id:
        qs = qs.filter(incident__school_class_id=filters.class_id)
    if filters.level_id:
        qs = qs.filter(incident__school_class__level_id=filters.level_id)
    if filters.section_id:
        qs = qs.filter(incident__school_class__section_id=filters.section_id)
    if filters.option_id:
        qs = qs.filter(incident__school_class__option_id=filters.option_id)
    qs = apply_date_range(qs, filters, field="summon_date")
    if filters.summons_status:
        qs = qs.filter(status=filters.summons_status)
    if filters.gender:
        qs = qs.filter(student__sexe=filters.gender)
    return qs
