"""French routes for the secretariat interface."""

from django.urls import path

from . import views

app_name = "secretariat"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("annees-scolaires/", views.AcademicYearListView.as_view(), name="academic-years"),
    path("annees-scolaires/nouvelle/", views.AcademicYearCreateView.as_view(), name="academic-year-create"),
    path("annees-scolaires/<uuid:public_id>/activer/", views.AcademicYearActionView.as_view(action="activate"), name="academic-year-activate"),
    path("annees-scolaires/<uuid:public_id>/cloturer/", views.AcademicYearActionView.as_view(action="close"), name="academic-year-close"),
    path("organisation/", views.OrganizationView.as_view(), name="organization"),
    path("niveaux/", views.OrganizationView.as_view(), {"tab": "levels"}, name="levels"),
    path("sections/", views.OrganizationView.as_view(), {"tab": "sections"}, name="sections"),
    path("options/", views.OrganizationView.as_view(), {"tab": "options"}, name="options"),
    path("classes/", views.ClassListView.as_view(), name="classes"),
    path("classes/nouvelle/", views.ClassCreateView.as_view(), name="class-create"),
    path("classes/<uuid:public_id>/", views.ClassDetailView.as_view(), name="class-detail"),
    path("eleves/", views.StudentListView.as_view(), name="students"),
    path("eleves/nouveau/", views.StudentCreateView.as_view(), name="student-create"),
    path("eleves/<uuid:public_id>/", views.StudentDetailView.as_view(), name="student-detail"),
    path("eleves/<uuid:public_id>/modifier/", views.StudentUpdateView.as_view(), name="student-update"),
    path("eleves/<uuid:public_id>/archiver/", views.StudentArchiveView.as_view(), name="student-archive"),
    path("responsables/", views.GuardianListView.as_view(), name="guardians"),
    path("responsables/<uuid:public_id>/", views.GuardianDetailView.as_view(), name="guardian-detail"),
    path("inscriptions/", views.EnrollmentListView.as_view(), name="enrollments"),
    path("inscriptions/nouvelle/", views.EnrollmentCreateView.as_view(), name="enrollment-create"),
    path("reinscriptions/", views.ReenrollmentView.as_view(), name="reenrollments"),
    path("reinscriptions/groupe/", views.BulkReenrollmentView.as_view(), name="reenrollments-bulk"),
    path("transferts/", views.TransferView.as_view(), name="transfers"),
    path("cartes/", views.CardListView.as_view(), name="cards"),
    path("cartes/<uuid:public_id>/", views.CardPreviewView.as_view(), name="card-preview"),
    path("cartes/generer/<uuid:public_id>/", views.CardGenerateView.as_view(), name="card-generate"),
    path("cartes/<uuid:public_id>/bloquer/", views.CardBlockView.as_view(), name="card-block"),
    path("communications/", views.CommunicationListView.as_view(), name="communications"),
    path("communications/nouvelle/", views.CommunicationCreateView.as_view(), name="communication-create"),
    path("communications/<uuid:public_id>/", views.CommunicationDetailView.as_view(), name="communication-detail"),
    path("communications/<uuid:public_id>/publier/", views.CommunicationPublishView.as_view(), name="communication-publish"),
    path("documents/", views.DocumentListView.as_view(), name="documents"),
    path("documents/<uuid:public_id>/telecharger/", views.DocumentDownloadView.as_view(), name="document-download"),
    path("documents/<uuid:public_id>/verifier/", views.DocumentVerifyView.as_view(), name="document-verify"),
    path("exports/eleves.<str:file_format>", views.ExportView.as_view(dataset="students"), name="students-export"),
    path("exports/inscriptions.<str:file_format>", views.ExportView.as_view(dataset="enrollments"), name="enrollments-export"),
]
