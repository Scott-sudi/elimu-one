"""Finance REST API views."""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import IsAccountant, IsSecretary
from apps.finance.models import FeeCategory, Payment, SchoolFee
from apps.finance.services import fee_approval_service, situation_service
from apps.finance.services.exceptions import FinanceError
from apps.secretariat.services.year_context import year_context_service

from .serializers import FeeCategorySerializer, PaymentSerializer, SchoolFeeSerializer


class AccountantAPIMixin:
    permission_classes = [IsAuthenticated, IsAccountant]

    def get_year(self):
        year = year_context_service.get_selected_year(self.request)
        if year is None:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Aucune année scolaire n'est sélectionnée.")
        return year


class FinanceDashboardAPIView(AccountantAPIMixin, APIView):
    def get(self, request):
        year = self.get_year()
        stats = situation_service.dashboard_stats(academic_year=year)

        def serialize(value):
            if hasattr(value, "quantize"):
                return str(value)
            if hasattr(value, "label") and hasattr(value, "public_id"):
                return {
                    "public_id": str(value.public_id),
                    "label": value.label,
                }
            if isinstance(value, dict):
                return {k: serialize(v) for k, v in value.items()}
            return value

        return Response(serialize(stats))


class FeeCategoryViewSet(AccountantAPIMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = FeeCategorySerializer
    lookup_field = "public_id"
    queryset = FeeCategory.objects.filter(is_active=True)


class SchoolFeeViewSet(AccountantAPIMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = SchoolFeeSerializer
    lookup_field = "public_id"

    def get_queryset(self):
        year = self.get_year()
        return SchoolFee.objects.filter(academic_year=year).select_related("category")


class PaymentViewSet(AccountantAPIMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    lookup_field = "public_id"

    def get_queryset(self):
        year = self.get_year()
        return Payment.objects.filter(academic_year=year).select_related("student")


class SecretaryFeeRequestViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsSecretary]
    serializer_class = SchoolFeeSerializer
    lookup_field = "public_id"

    def get_queryset(self):
        year = year_context_service.get_selected_year(self.request)
        qs = SchoolFee.objects.filter(status=SchoolFee.Status.PENDING).select_related(
            "category", "academic_year"
        )
        if year:
            qs = qs.filter(academic_year=year)
        return qs

    @action(detail=True, methods=["post"])
    def approve(self, request, public_id=None):
        fee = self.get_object()
        try:
            fee_approval_service.approve_fee(fee=fee, actor=request.user, request=request)
        except FinanceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        fee.refresh_from_db()
        return Response(SchoolFeeSerializer(fee).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, public_id=None):
        fee = self.get_object()
        reason = (request.data.get("rejection_reason") or "").strip()
        try:
            fee_approval_service.reject_fee(
                fee=fee,
                rejection_reason=reason,
                actor=request.user,
                request=request,
            )
        except FinanceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        fee.refresh_from_db()
        return Response(SchoolFeeSerializer(fee).data)
