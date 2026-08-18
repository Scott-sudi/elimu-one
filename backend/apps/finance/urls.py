"""French routes for the finance (comptabilité) interface."""

from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("frais/", views.FeeListView.as_view(), name="fees"),
    path("frais/nouveau/", views.FeeCreateView.as_view(), name="fee-create"),
    path("frais/<uuid:public_id>/", views.FeeDetailView.as_view(), name="fee-detail"),
    path(
        "frais/<uuid:public_id>/soumettre/",
        views.FeeSubmitView.as_view(),
        name="fee-submit",
    ),
    path(
        "frais/<uuid:public_id>/retirer/",
        views.FeeWithdrawView.as_view(),
        name="fee-withdraw",
    ),
    path(
        "frais/<uuid:public_id>/archiver/",
        views.FeeArchiveView.as_view(),
        name="fee-archive",
    ),
    path("demandes/", views.FeeRequestsRedirectView.as_view(), name="fee-requests"),
    path("classes/", views.ClassListView.as_view(), name="classes"),
    path(
        "classes/<uuid:public_id>/situation/",
        views.ClassSituationView.as_view(),
        name="class-situation",
    ),
    path(
        "classes/<uuid:public_id>/montant-frais/",
        views.ClassFeeAmountChangeView.as_view(),
        name="class-fee-amount-change",
    ),
    path(
        "classes/<uuid:public_id>/autres-frais/",
        views.ClassOtherFeeCreateView.as_view(),
        name="class-other-fee-create",
    ),
    path(
        "eleves/<uuid:public_id>/situation/",
        views.StudentSituationView.as_view(),
        name="student-situation",
    ),
    path("eleves/recherche/", views.StudentSearchView.as_view(), name="student-search"),
    path(
        "cartes/resoudre/",
        views.CardScanResolveView.as_view(),
        name="card-scan-resolve",
    ),
    path("paiements/", views.PaymentListView.as_view(), name="payments"),
    path("paiements/nouveau/", views.PaymentCreateView.as_view(), name="payment-create"),
    path(
        "paiements/matricule/",
        views.PaymentMatriculeLookupView.as_view(),
        name="payment-matricule-lookup",
    ),
    path(
        "paiements/<uuid:public_id>/",
        views.PaymentDetailView.as_view(),
        name="payment-detail",
    ),
    path(
        "paiements/<uuid:public_id>/annuler/",
        views.PaymentCancelView.as_view(),
        name="payment-cancel",
    ),
    path("recus/", views.ReceiptListView.as_view(), name="receipts"),
    path("recus/<uuid:public_id>/", views.ReceiptDetailView.as_view(), name="receipt-detail"),
    path(
        "recus/<uuid:public_id>/pdf/",
        views.ReceiptPDFView.as_view(),
        name="receipt-pdf",
    ),
    path("impayes/", views.ArrearsListView.as_view(), name="arrears"),
    path("rapports/", views.ReportsIndexView.as_view(), name="reports"),
    path(
        "rapports/paiements.csv",
        views.PaymentsPeriodExportView.as_view(),
        name="reports-payments-csv",
    ),
    path(
        "rapports/paiements.xlsx",
        views.PaymentsPeriodExportView.as_view(),
        name="reports-payments-xlsx",
    ),
    path(
        "rapports/paiements.pdf",
        views.PaymentsPeriodExportView.as_view(),
        name="reports-payments-pdf",
    ),
    path(
        "rapports/impayes.export",
        views.ArrearsExportView.as_view(),
        name="reports-arrears-export",
    ),
]
