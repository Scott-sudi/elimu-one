"""BI API URL routes."""

from django.urls import path

from .views import (
    AttendanceClassesAPIView,
    AttendanceSummaryAPIView,
    AttendanceTrendsAPIView,
    ClassesClassesAPIView,
    ClassesSummaryAPIView,
    ClassesTrendsAPIView,
    ComparisonsSummaryAPIView,
    ComparisonsTrendsAPIView,
    DisciplineClassesAPIView,
    DisciplineSummaryAPIView,
    DisciplineTrendsAPIView,
    EnrollmentClassesAPIView,
    EnrollmentSummaryAPIView,
    EnrollmentTrendsAPIView,
    FinancialClassesAPIView,
    FinancialSummaryAPIView,
    FinancialTrendsAPIView,
    OverviewAPIView,
)

app_name = "bi-api"

urlpatterns = [
    path("overview/", OverviewAPIView.as_view(), name="overview"),
    path("enrollments/summary/", EnrollmentSummaryAPIView.as_view(), name="enrollments-summary"),
    path("enrollments/trends/", EnrollmentTrendsAPIView.as_view(), name="enrollments-trends"),
    path("enrollments/classes/", EnrollmentClassesAPIView.as_view(), name="enrollments-classes"),
    path("financial/summary/", FinancialSummaryAPIView.as_view(), name="financial-summary"),
    path("financial/trends/", FinancialTrendsAPIView.as_view(), name="financial-trends"),
    path("financial/classes/", FinancialClassesAPIView.as_view(), name="financial-classes"),
    path("attendance/summary/", AttendanceSummaryAPIView.as_view(), name="attendance-summary"),
    path("attendance/trends/", AttendanceTrendsAPIView.as_view(), name="attendance-trends"),
    path("attendance/classes/", AttendanceClassesAPIView.as_view(), name="attendance-classes"),
    path("discipline/summary/", DisciplineSummaryAPIView.as_view(), name="discipline-summary"),
    path("discipline/trends/", DisciplineTrendsAPIView.as_view(), name="discipline-trends"),
    path("discipline/classes/", DisciplineClassesAPIView.as_view(), name="discipline-classes"),
    path("classes/summary/", ClassesSummaryAPIView.as_view(), name="classes-summary"),
    path("classes/trends/", ClassesTrendsAPIView.as_view(), name="classes-trends"),
    path("classes/classes/", ClassesClassesAPIView.as_view(), name="classes-classes"),
    path("comparisons/summary/", ComparisonsSummaryAPIView.as_view(), name="comparisons-summary"),
    path("comparisons/trends/", ComparisonsTrendsAPIView.as_view(), name="comparisons-trends"),
]
