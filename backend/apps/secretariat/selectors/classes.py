"""School class query helpers."""

from __future__ import annotations

from django.db.models import Count, F, IntegerField, Q, QuerySet, Value
from django.db.models.functions import Greatest

from apps.secretariat.models import Enrollment, SchoolClass


def class_queryset() -> QuerySet[SchoolClass]:
    return SchoolClass.objects.select_related(
        "academic_year", "level", "section", "option",
    ).annotate(
        enrollment_count=Count(
            "enrollments",
            filter=Q(enrollments__status=Enrollment.Status.VALIDATED),
        ),
    ).annotate(
        remaining_capacity=Greatest(
            F("max_capacity") - F("enrollment_count"),
            Value(0),
            output_field=IntegerField(),
        ),
    )


def search_classes(
    *,
    query: str = "",
    academic_year=None,
    level=None,
    section=None,
    option=None,
    active_only: bool = True,
) -> QuerySet[SchoolClass]:
    classes = class_queryset()
    if query:
        classes = classes.filter(Q(name__icontains=query) | Q(code__icontains=query))
    if academic_year:
        classes = classes.filter(academic_year=academic_year)
    if level:
        classes = classes.filter(level=level)
    if section:
        classes = classes.filter(section=section)
    if option:
        classes = classes.filter(option=option)
    if active_only:
        classes = classes.filter(is_active=True)
    return classes
