"""Finance API URL routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FeeCategoryViewSet,
    FinanceDashboardAPIView,
    PaymentViewSet,
    SchoolFeeViewSet,
    SecretaryFeeRequestViewSet,
)

app_name = "finance-api"

router = DefaultRouter()
router.register(r"fee-categories", FeeCategoryViewSet, basename="fee-categories")
router.register(r"fees", SchoolFeeViewSet, basename="fees")
router.register(r"payments", PaymentViewSet, basename="payments")
router.register(r"fee-requests", SecretaryFeeRequestViewSet, basename="fee-requests")

urlpatterns = [
    path("dashboard/", FinanceDashboardAPIView.as_view(), name="dashboard"),
    path("", include(router.urls)),
]
