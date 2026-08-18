"""Attendance querysets for BI."""

from __future__ import annotations

from django.db.models import QuerySet

from apps.bi.filters import BiFilters, apply_class_structure_filters, apply_date_range
from apps.discipline.models import DailyAttendance
from apps.secretariat.models import AcademicYear


def attendance_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> QuerySet[DailyAttendance]:
    qs = DailyAttendance.objects.filter(academic_year=academic_year).select_related(
        "enrollment",
        "enrollment__school_class",
        "student",
    )
    filters = filters or BiFilters()
    qs = apply_class_structure_filters(qs, filters, class_prefix="enrollment__school_class")
    qs = apply_date_range(qs, filters, field="date")
    if filters.attendance_status:
        qs = qs.filter(status=filters.attendance_status)
    if filters.gender:
        qs = qs.filter(student__sexe=filters.gender)
    return qs
