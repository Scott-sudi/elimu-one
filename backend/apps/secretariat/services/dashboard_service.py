"""Database-backed secretary dashboard statistics."""

from __future__ import annotations

from django.db.models import Count, F, Q, Sum

from apps.secretariat.models import AcademicYear, Enrollment, SchoolClass, Student


def get_dashboard_stats(*, academic_year: AcademicYear | None = None) -> dict:
    academic_year = academic_year or AcademicYear.objects.filter(is_active=True, is_closed=False).first()
    enrollments = Enrollment.objects.none()
    classes = SchoolClass.objects.none()
    if academic_year:
        enrollments = Enrollment.objects.filter(academic_year=academic_year)
        classes = SchoolClass.objects.filter(academic_year=academic_year, is_active=True)

    enrollment_stats = enrollments.aggregate(
        total=Count("id", filter=Q(status=Enrollment.Status.VALIDATED)),
        girls=Count(
            "id",
            filter=Q(status=Enrollment.Status.VALIDATED, student__sexe=Student.Gender.FEMALE),
        ),
        boys=Count(
            "id",
            filter=Q(status=Enrollment.Status.VALIDATED, student__sexe=Student.Gender.MALE),
        ),
    )
    capacity = classes.aggregate(total=Sum("max_capacity"))["total"] or 0
    validated = enrollment_stats["total"] or 0

    classes_with_stats = classes.annotate(
        occupied=Count(
            "enrollments",
            filter=Q(enrollments__status=Enrollment.Status.VALIDATED),
        ),
        girls=Count(
            "enrollments",
            filter=Q(
                enrollments__status=Enrollment.Status.VALIDATED,
                enrollments__student__sexe=Student.Gender.FEMALE,
            ),
        ),
        boys=Count(
            "enrollments",
            filter=Q(
                enrollments__status=Enrollment.Status.VALIDATED,
                enrollments__student__sexe=Student.Gender.MALE,
            ),
        ),
    ).order_by("level__order", "name")

    class_gender_rows = [
        {
            "public_id": school_class.public_id,
            "name": school_class.name,
            "code": school_class.code,
            "girls": school_class.girls,
            "boys": school_class.boys,
            "total": school_class.girls + school_class.boys,
        }
        for school_class in classes_with_stats
    ]
    class_free_place_rows = [
        {
            "public_id": school_class.public_id,
            "name": school_class.name,
            "code": school_class.code,
            "free_places": school_class.max_capacity - school_class.occupied,
            "capacity": school_class.max_capacity,
            "occupied": school_class.occupied,
        }
        for school_class in classes_with_stats
        if school_class.occupied < school_class.max_capacity
    ]

    full_classes = classes_with_stats.filter(occupied__gte=F("max_capacity")).count()
    free_classes = len(class_free_place_rows)

    return {
        "academic_year": academic_year,
        "enrollments": {
            "total": validated,
            "girls": enrollment_stats["girls"] or 0,
            "boys": enrollment_stats["boys"] or 0,
        },
        "classes": {
            "total": classes.count(),
            "capacity": capacity,
            "occupied": validated,
            "occupancy_percentage": round(validated * 100 / capacity, 1) if capacity else 0,
            "full": full_classes,
            "with_free_places": free_classes,
        },
        "class_gender_rows": class_gender_rows,
        "class_free_place_rows": class_free_place_rows,
    }
