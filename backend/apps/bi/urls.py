"""French routes for the BI (Préfet) interface."""

from django.urls import path

from . import views

app_name = "bi"

urlpatterns = [
    path("", views.OverviewView.as_view(), name="overview"),
    path("effectifs/", views.EnrollmentsView.as_view(), name="enrollments"),
    path("finances/", views.FinancialView.as_view(), name="finance"),
    path("assiduite/", views.AttendanceView.as_view(), name="attendance"),
    path("discipline/", views.DisciplineAnalyticsView.as_view(), name="discipline"),
    path("classes/", views.ClassesView.as_view(), name="classes"),
    path("comparaisons/", views.ComparisonsView.as_view(), name="comparisons"),
    path("rapports/", views.ReportsView.as_view(), name="reports"),
    path(
        "rapports/export/<str:domain>.<str:file_format>/",
        views.BiExportDownloadView.as_view(),
        name="export-download",
    ),
]
