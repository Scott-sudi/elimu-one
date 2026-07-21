"""Secretariat API routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AcademicYearViewSet,
    CommunicationViewSet,
    EnrollmentViewSet,
    GuardianViewSet,
    OptionViewSet,
    SchoolClassViewSet,
    SchoolLevelViewSet,
    SectionViewSet,
    StudentCardViewSet,
    StudentViewSet,
)

app_name = "secretariat-api"

router = DefaultRouter()
router.register(r"academic-years", AcademicYearViewSet, basename="academic-years")
router.register(r"levels", SchoolLevelViewSet, basename="levels")
router.register(r"sections", SectionViewSet, basename="sections")
router.register(r"options", OptionViewSet, basename="options")
router.register(r"classes", SchoolClassViewSet, basename="classes")
router.register(r"students", StudentViewSet, basename="students")
router.register(r"guardians", GuardianViewSet, basename="guardians")
router.register(r"enrollments", EnrollmentViewSet, basename="enrollments")
router.register(r"student-cards", StudentCardViewSet, basename="student-cards")
router.register(r"communications", CommunicationViewSet, basename="communications")

urlpatterns = [
    path("", include(router.urls)),
]
