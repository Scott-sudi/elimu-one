"""French routes for discipline interface."""

from django.urls import path

from . import views
from .views_schedules import AttendanceSchedulesView

app_name = "discipline"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("horaires/", AttendanceSchedulesView.as_view(), name="schedules"),
    path("pointage/", views.AttendanceScanView.as_view(), name="attendance-scan"),
    path("scanner/resolve/", views.DisciplineScannerResolveView.as_view(), name="scanner-resolve"),
    path("scanner/attendance/scan/", views.DisciplineScannerAttendanceScanView.as_view(), name="scanner-attendance-scan"),
    path(
        "students/<uuid:public_id>/conduct-summary/",
        views.DisciplineStudentConductSummaryView.as_view(),
        name="scanner-conduct-summary",
    ),
    path("pointage/scan/", views.AttendanceScanSubmitView.as_view(), name="attendance-scan-submit"),
    path("pointage/manuel/", views.AttendanceManualSubmitView.as_view(), name="attendance-manual-submit"),
    path("presences/", views.DailyAttendanceView.as_view(), name="attendance-daily"),
    path("classes/", views.ClassConductListView.as_view(), name="classes"),
    path(
        "classes/<uuid:class_id>/presences/",
        views.ClassAttendanceFoldersView.as_view(),
        name="class-attendance-folders",
    ),
    path(
        "classes/<uuid:class_id>/presences/<slug:sheet_date>/",
        views.ClassAttendanceSheetView.as_view(),
        name="class-attendance-sheet",
    ),
    path(
        "classes/<uuid:class_id>/presences/<slug:sheet_date>/imprimer/",
        views.ClassAttendanceSheetPrintView.as_view(),
        name="class-attendance-sheet-print",
    ),
    path(
        "classes/<uuid:class_id>/presences/<slug:sheet_date>/export/csv/",
        views.ClassAttendanceSheetCsvExportView.as_view(),
        name="class-attendance-sheet-export-csv",
    ),
    path("eleves/", views.StudentConductListView.as_view(), name="students"),
    path(
        "eleves/<uuid:public_id>/dossier/",
        views.StudentDisciplinaryFileView.as_view(),
        name="student-disciplinary-file",
    ),
    path(
        "eleves/<uuid:public_id>/dossier/imprimer/",
        views.StudentDisciplinaryFilePrintView.as_view(),
        name="student-disciplinary-file-print",
    ),
    path(
        "eleves/<uuid:public_id>/dossier/pdf/",
        views.StudentDisciplinaryFilePdfView.as_view(),
        name="student-disciplinary-file-pdf",
    ),
    path("conduite/", views.ConductView.as_view(), name="conduct"),
    path("incidents/", views.IncidentListView.as_view(), name="incidents"),
    path(
        "incidents/eleve-lookup/",
        views.IncidentStudentLookupView.as_view(),
        name="incident-student-lookup",
    ),
    path(
        "incidents/<uuid:public_id>/",
        views.IncidentDetailView.as_view(),
        name="incident-detail",
    ),
    path("mesures/", views.MeasureListView.as_view(), name="measures"),
    path("convocations/", views.SummonsListView.as_view(), name="summons"),
    path("sorties/", views.ExitAuthorizationListView.as_view(), name="exits"),
    path(
        "sorties/<uuid:public_id>/",
        views.ExitAuthorizationDetailView.as_view(),
        name="exit-detail",
    ),
    path("justificatifs/", views.JustificationListView.as_view(), name="justifications"),
    path("suivi/", views.CaseFollowupView.as_view(), name="followup"),
    path(
        "suivi/classes/<uuid:class_id>/",
        views.CaseFollowupClassView.as_view(),
        name="followup-class",
    ),
]

