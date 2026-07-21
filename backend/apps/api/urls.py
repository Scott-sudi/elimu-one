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
        "cards/resolve/<str:qr_identifier>/",
        CardResolveAPIView.as_view(),
        name="card-resolve",
    ),
    path("", include(router.urls)),
]
