"""Class-centric querysets for BI."""

from __future__ import annotations

from django.db.models import Count, Q, QuerySet

from apps.bi.filters import BiFilters
from apps.bi.selectors.enrollment_selectors import active_classes_qs
from apps.secretariat.models import AcademicYear, Enrollment, SchoolClass


def classes_analytics_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> QuerySet[SchoolClass]:
    """Active classes annotated with validated enrollment count."""
    return active_classes_qs(academic_year, filters).annotate(
        occupied=Count(
            "enrollments",
            filter=Q(enrollments__status=Enrollment.Status.VALIDATED),
        ),
        boys=Count(
            "enrollments",
            filter=Q(
                enrollments__status=Enrollment.Status.VALIDATED,
                enrollments__student__sexe="M",
            ),
        ),
        girls=Count(
            "enrollments",
            filter=Q(
                enrollments__status=Enrollment.Status.VALIDATED,
                enrollments__student__sexe="F",
            ),
        ),
    ).order_by("level__order", "name")
