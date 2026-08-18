"""API v1 URL routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.api.views import (
    AuditLogViewSet,
    ChangePasswordAPIView,
    DashboardAPIView,
    HealthView,
    KalungaTokenObtainPairView,
    KalungaTokenRefreshView,
    LoginAttemptViewSet,
    LogoutAPIView,
    MeAPIView,
    RoleViewSet,
    SetupInitializeView,
    SetupStatusView,
    UserResetPasswordAPIView,
    UserStatusAPIView,
    UserViewSet,
)
from apps.api.parents_auth import ParentPhoneVerifyAPIView
from apps.api.parents_children import ParentChildrenListAPIView
from apps.api.parents_child_modules import (
    ParentChildAttendanceAPIView,
    ParentChildDisciplineAPIView,
    ParentChildFinanceAPIView,
)
from apps.api.parents_child_card import ParentChildCardAPIView
from apps.api.parents_home import ParentHomeOverviewAPIView
from apps.api.parents_notifications import ParentNotificationsAPIView
from apps.api.parents_devices import ParentDeviceRegisterAPIView
from apps.api.parents_profile import ParentProfileAPIView
from apps.api.parents_notification_details import (
    ParentCommunicationDetailAPIView,
    ParentDisciplineDetailAPIView,
    ParentPaymentReceiptAPIView,
    ParentPaymentReceiptPdfAPIView,
)
from apps.secretariat.api.views import CardResolveAPIView

app_name = "api"

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")
router.register(r"roles", RoleViewSet, basename="roles")
router.register(r"audit/logins", LoginAttemptViewSet, basename="audit-logins")
router.register(r"audit/actions", AuditLogViewSet, basename="audit-actions")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("setup/status/", SetupStatusView.as_view(), name="setup-status"),
    path("setup/initialize/", SetupInitializeView.as_view(), name="setup-initialize"),
    path("auth/token/", KalungaTokenObtainPairView.as_view(), name="token"),
    path("auth/token/refresh/", KalungaTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("auth/me/", MeAPIView.as_view(), name="me"),
    path("auth/change-password/", ChangePasswordAPIView.as_view(), name="change-password"),
    path(
        "parents/auth/verify-phone/",
        ParentPhoneVerifyAPIView.as_view(),
        name="parents-verify-phone",
    ),
    path(
        "parents/children/",
        ParentChildrenListAPIView.as_view(),
        name="parents-children",
    ),
    path(
        "parents/home/overview/",
        ParentHomeOverviewAPIView.as_view(),
        name="parents-home-overview",
    ),
    path(
        "parents/notifications/",
        ParentNotificationsAPIView.as_view(),
        name="parents-notifications",
    ),
    path(
        "parents/devices/register/",
        ParentDeviceRegisterAPIView.as_view(),
        name="parents-device-register",
    ),
    path(
        "parents/communications/<uuid:public_id>/",
        ParentCommunicationDetailAPIView.as_view(),
        name="parents-communication-detail",
    ),
    path(
        "parents/payments/<uuid:public_id>/",
        ParentPaymentReceiptAPIView.as_view(),
        name="parents-payment-receipt",
    ),
    path(
        "parents/payments/<uuid:public_id>/receipt.pdf",
        ParentPaymentReceiptPdfAPIView.as_view(),
        name="parents-payment-receipt-pdf",
    ),
    path(
        "parents/discipline/<str:kind>/<uuid:public_id>/",
        ParentDisciplineDetailAPIView.as_view(),
        name="parents-discipline-detail",
    ),
    path(
        "parents/profile/",
        ParentProfileAPIView.as_view(),
        name="parents-profile",
    ),
    path(
        "parents/children/<uuid:student_public_id>/attendance/",
        ParentChildAttendanceAPIView.as_view(),
        name="parents-child-attendance",
    ),
    path(
        "parents/children/<uuid:student_public_id>/discipline/",
        ParentChildDisciplineAPIView.as_view(),
        name="parents-child-discipline",
    ),
    path(
        "parents/children/<uuid:student_public_id>/finance/",
        ParentChildFinanceAPIView.as_view(),
        name="parents-child-finance",
    ),
    path(
        "parents/children/<uuid:student_public_id>/card/",
        ParentChildCardAPIView.as_view(),
        name="parents-child-card",
    ),
    path("admin/dashboard/", DashboardAPIView.as_view(), name="admin-dashboard"),
    path("users/<uuid:public_id>/status/", UserStatusAPIView.as_view(), name="user-status"),
    path(
        "users/<uuid:public_id>/reset-password/",
        UserResetPasswordAPIView.as_view(),
        name="user-reset-password",
    ),
    path(
        "secretariat/",
        include(("apps.secretariat.api.urls", "secretariat-api")),
    ),
    path(
        "finance/",
        include(("apps.finance.api.urls", "finance-api")),
    ),
    path(
        "bi/",
        include(("apps.bi.api.urls", "bi-api")),
    ),
    path(
        "cards/resolve/<str:qr_identifier>/",
        CardResolveAPIView.as_view(),
        name="card-resolve",
    ),
    path("", include(router.urls)),
]
