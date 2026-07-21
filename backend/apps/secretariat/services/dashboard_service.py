"""Database-backed secretary dashboard statistics."""

from __future__ import annotations

from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.secretariat.models import (
    AcademicYear,
    Communication,
    Enrollment,
    SchoolClass,
    Student,
    StudentDocument,
)


def get_dashboard_stats(*, academic_year: AcademicYear | None = None) -> dict:
    academic_year = academic_year or AcademicYear.objects.filter(is_active=True).first()
    enrollments = Enrollment.objects.none()
    classes = SchoolClass.objects.none()
    if academic_year:
        enrollments = Enrollment.objects.filter(academic_year=academic_year)
        classes = SchoolClass.objects.filter(academic_year=academic_year, is_active=True)

    enrollment_stats = enrollments.aggregate(
        total=Count("id", filter=Q(status=Enrollment.Status.VALIDATED)),
        drafts=Count("id", filter=Q(status=Enrollment.Status.DRAFT)),
        girls=Count("id", filter=Q(status=Enrollment.Status.VALIDATED, student__sexe=Student.Gender.FEMALE)),
        boys=Count("id", filter=Q(status=Enrollment.Status.VALIDATED, student__sexe=Student.Gender.MALE)),
    )
    capacity = classes.aggregate(total=Sum("max_capacity"))["total"] or 0
    validated = enrollment_stats["total"] or 0
    return {
        "academic_year": academic_year,
        "students": {
            "active": Student.objects.filter(is_active=True, is_archived=False).count(),
            "archived": Student.objects.filter(is_archived=True).count(),
        },
        "enrollments": enrollment_stats,
        "classes": {
            "total": classes.count(),
            "capacity": capacity,
            "occupied": validated,
            "occupancy_percentage": round(validated * 100 / capacity, 1) if capacity else 0,
            "full": classes.annotate(
                occupied=Count("enrollments", filter=Q(enrollments__status=Enrollment.Status.VALIDATED)),
            ).filter(occupied__gte=F("max_capacity")).count(),
        },
        "documents_pending": StudentDocument.objects.filter(
            verification_status=StudentDocument.VerificationStatus.PENDING,
        ).count(),
        "communications": {
            "published": Communication.objects.filter(status=Communication.Status.PUBLISHED).count(),
            "scheduled": Communication.objects.filter(
                status=Communication.Status.SCHEDULED,
                published_at__gte=timezone.now(),
            ).count(),
        },
    }
