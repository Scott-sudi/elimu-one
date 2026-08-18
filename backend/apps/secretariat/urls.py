"""French routes for the secretariat interface."""

from django.urls import path

from . import views

app_name = "secretariat"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("choisir-annee/", views.AcademicYearSelectView.as_view(), name="academic-year-select"),
    path(
        "choisir-annee/<uuid:public_id>/",
        views.AcademicYearChooseView.as_view(),
        name="academic-year-choose",
    ),
    path("changer-annee/", views.AcademicYearChangeView.as_view(), name="academic-year-change"),
    path("annees-scolaires/", views.AcademicYearListView.as_view(), name="academic-years"),
    path("annees-scolaires/nouvelle/", views.AcademicYearCreateView.as_view(), name="academic-year-create"),
    path(
        "annees-scolaires/<uuid:public_id>/modifier/",
        views.AcademicYearUpdateView.as_view(),
        name="academic-year-update",
    ),
    path(
        "annees-scolaires/<uuid:public_id>/supprimer/",
        views.AcademicYearDeleteView.as_view(),
        name="academic-year-delete",
    ),
    path(
        "annees-scolaires/<uuid:public_id>/activer/",
        views.AcademicYearActionView.as_view(action="activate"),
        name="academic-year-activate",
    ),
    path(
        "annees-scolaires/<uuid:public_id>/cloturer/",
        views.AcademicYearActionView.as_view(action="close"),
        name="academic-year-close",
    ),
    path(
        "annees-scolaires/declarer-fin/",
        views.AcademicYearDeclareCloseView.as_view(),
        name="academic-year-declare-close",
    ),
    path("organisation/", views.OrganizationView.as_view(), name="organization"),
    path("niveaux/", views.OrganizationView.as_view(), {"tab": "levels"}, name="levels"),
    path("sections/", views.OrganizationView.as_view(), {"tab": "sections"}, name="sections"),
    path("options/", views.OrganizationView.as_view(), {"tab": "options"}, name="options"),
    path(
        "niveaux/<uuid:public_id>/",
        views.LevelActionView.as_view(),
        name="level-action",
    ),
    path(
        "sections/<uuid:public_id>/",
        views.SectionActionView.as_view(),
        name="section-action",
    ),
    path(
        "options/<uuid:public_id>/",
        views.OptionActionView.as_view(),
        name="option-action",
    ),
    path("classes/", views.ClassListView.as_view(), name="classes"),
    path("classes/nouvelle/", views.ClassCreateView.as_view(), name="class-create"),
    path("classes/<uuid:public_id>/", views.ClassDetailView.as_view(), name="class-detail"),
    path(
        "classes/<uuid:public_id>/modifier/",
        views.ClassUpdateView.as_view(),
        name="class-update",
    ),
    path(
        "classes/<uuid:public_id>/desactiver/",
        views.ClassActionView.as_view(action="deactivate"),
        name="class-deactivate",
    ),
    path(
        "classes/<uuid:public_id>/reactiver/",
        views.ClassActionView.as_view(action="reactivate"),
        name="class-reactivate",
    ),
    path(
        "classes/<uuid:public_id>/supprimer/",
        views.ClassActionView.as_view(action="delete"),
        name="class-delete",
    ),
    path(
        "classes/<uuid:public_id>/elargir-places/",
        views.ClassActionView.as_view(action="expand_capacity"),
        name="class-expand-capacity",
    ),
    path(
        "classes/<uuid:public_id>/cartes.zip",
        views.ClassCardsZipDownloadView.as_view(),
        name="class-cards-zip",
    ),
    path(
        "classes/<uuid:public_id>/inscription/",
        views.ClassInscriptionView.as_view(),
        name="class-enroll",
    ),
    path(
        "classes/<uuid:public_id>/reinscription/",
        views.ClassReenrollmentView.as_view(),
        name="class-reenroll",
    ),
    path(
        "classes/<uuid:public_id>/reinscription/groupe/",
        views.ClassBulkReenrollmentView.as_view(),
        name="class-reenroll-bulk",
    ),
    path(
        "responsables/recherche-telephone/",
        views.GuardianPhoneLookupView.as_view(),
        name="guardian-phone-lookup",
    ),
    path("eleves/", views.StudentListView.as_view(), name="students"),
    path("eleves/nouveau/", views.StudentCreateView.as_view(), name="student-create"),
    path("eleves/<uuid:public_id>/", views.StudentDetailView.as_view(), name="student-detail"),
    path("eleves/<uuid:public_id>/modifier/", views.StudentUpdateView.as_view(), name="student-update"),
    path("eleves/<uuid:public_id>/archiver/", views.StudentArchiveView.as_view(), name="student-archive"),
    path("eleves/<uuid:public_id>/supprimer/", views.StudentDeleteView.as_view(), name="student-delete"),
    path("eleves/<uuid:public_id>/restaurer/", views.StudentRestoreView.as_view(), name="student-restore"),
    path("responsables/", views.GuardianListView.as_view(), name="guardians"),
    path("responsables/<uuid:public_id>/", views.GuardianDetailView.as_view(), name="guardian-detail"),
    path(
        "responsables/<uuid:public_id>/modifier/",
        views.GuardianUpdateView.as_view(),
        name="guardian-update",
    ),
    path(
        "responsables/<uuid:public_id>/archiver/",
        views.GuardianArchiveView.as_view(),
        name="guardian-archive",
    ),
    path(
        "responsables/<uuid:public_id>/restaurer/",
        views.GuardianRestoreView.as_view(),
        name="guardian-restore",
    ),
    path("inscriptions/", views.EnrollmentListView.as_view(), name="enrollments"),
    path("inscriptions/nouvelle/", views.EnrollmentCreateView.as_view(), name="enrollment-create"),
    path("reinscriptions/", views.ReenrollmentView.as_view(), name="reenrollments"),
    path("reinscriptions/groupe/", views.BulkReenrollmentView.as_view(), name="reenrollments-bulk"),
    path("transferts/", views.TransferView.as_view(), name="transfers"),
    path("cartes/", views.CardListView.as_view(), name="cards"),
    path("cartes/<uuid:public_id>/", views.CardPreviewView.as_view(), name="card-preview"),
    path("cartes/<uuid:public_id>/image.png", views.CardPngDownloadView.as_view(), name="card-png"),
    path("cartes/generer/<uuid:public_id>/", views.CardGenerateView.as_view(), name="card-generate"),
    path("cartes/<uuid:public_id>/bloquer/", views.CardBlockView.as_view(), name="card-block"),
    path("communications/", views.CommunicationListView.as_view(), name="communications"),
    path(
        "communications/eleves-classe/",
        views.CommunicationClassStudentsView.as_view(),
        name="communication-class-students",
    ),
    path("communications/nouvelle/", views.CommunicationCreateView.as_view(), name="communication-create"),
    path(
        "communications/<uuid:public_id>/",
        views.CommunicationDetailView.as_view(),
        name="communication-detail",
    ),
    path(
        "communications/<uuid:public_id>/modifier/",
        views.CommunicationUpdateView.as_view(),
        name="communication-update",
    ),
    path(
        "communications/<uuid:public_id>/supprimer/",
        views.CommunicationDeleteView.as_view(),
        name="communication-delete",
    ),
    path(
        "communications/<uuid:public_id>/publier/",
        views.CommunicationPublishView.as_view(),
        name="communication-publish",
    ),
    path(
        "communications/<uuid:public_id>/epingler/",
        views.CommunicationPinView.as_view(),
        name="communication-pin",
    ),
    path(
        "communications/<uuid:public_id>/desepingler/",
        views.CommunicationUnpinView.as_view(),
        name="communication-unpin",
    ),
    path(
        "communications/<uuid:public_id>/archiver/",
        views.CommunicationArchiveView.as_view(),
        name="communication-archive",
    ),
    path(
        "communications/<uuid:public_id>/restaurer/",
        views.CommunicationRestoreView.as_view(),
        name="communication-restore",
    ),
    path("documents/", views.DocumentListView.as_view(), name="documents"),
    path(
        "documents/<uuid:public_id>/telecharger/",
        views.DocumentDownloadView.as_view(),
        name="document-download",
    ),
    path(
        "documents/<uuid:public_id>/verifier/",
        views.DocumentVerifyView.as_view(),
        name="document-verify",
    ),
    path("exports/eleves.<str:file_format>", views.ExportView.as_view(dataset="students"), name="students-export"),
    path(
        "exports/inscriptions.<str:file_format>",
        views.ExportView.as_view(dataset="enrollments"),
        name="enrollments-export",
    ),
    path("validation-frais/", views.FeeApprovalListView.as_view(), name="fee-approvals"),
    path(
        "validation-frais/<uuid:public_id>/",
        views.FeeApprovalDetailView.as_view(),
        name="fee-approval-detail",
    ),
    path(
        "validation-frais/<uuid:public_id>/approuver/",
        views.FeeApproveView.as_view(),
        name="fee-approve",
    ),
    path(
        "validation-frais/<uuid:public_id>/rejeter/",
        views.FeeRejectView.as_view(),
        name="fee-reject",
    ),
    path(
        "validation-montants/<uuid:public_id>/",
        views.FeeAmountChangeDetailView.as_view(),
        name="fee-amount-change-detail",
    ),
    path(
        "validation-montants/<uuid:public_id>/approuver/",
        views.FeeAmountChangeApproveView.as_view(),
        name="fee-amount-change-approve",
    ),
    path(
        "validation-montants/<uuid:public_id>/rejeter/",
        views.FeeAmountChangeRejectView.as_view(),
        name="fee-amount-change-reject",
    ),
]
