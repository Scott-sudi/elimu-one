"""Finance API serializers."""

from __future__ import annotations

from rest_framework import serializers

from apps.finance.models import FeeCategory, Payment, SchoolFee, StudentFeeObligation
from apps.finance.services import fee_approval_service, fee_service, payment_service
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.password import require_password


class FeeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeCategory
        fields = ("public_id", "code", "name", "description", "order", "is_active")


class SchoolFeeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SchoolFee
        fields = (
            "public_id",
            "code",
            "label",
            "description",
            "amount",
            "currency",
            "due_date",
            "is_mandatory",
            "allow_partial",
            "application_type",
            "status",
            "status_display",
            "category",
            "category_name",
            "rejection_reason",
            "submitted_at",
            "reviewed_at",
            "is_active",
            "is_archived",
            "created_at",
        )
        read_only_fields = (
            "status",
            "rejection_reason",
            "submitted_at",
            "reviewed_at",
            "is_archived",
            "created_at",
        )


class ObligationSerializer(serializers.ModelSerializer):
    fee_label = serializers.CharField(source="fee.label", read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = StudentFeeObligation
        fields = (
            "public_id",
            "fee_label",
            "amount_due",
            "amount_paid",
            "balance",
            "status",
            "currency",
        )

    def get_balance(self, obj):
        return obj.amount_due - obj.amount_paid


class PaymentSerializer(serializers.ModelSerializer):
    student_matricule = serializers.CharField(source="student.matricule", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "public_id",
            "receipt_number",
            "payment_date",
            "amount_total",
            "currency",
            "payment_method",
            "transaction_reference",
            "payer_name",
            "status",
            "status_display",
            "student_matricule",
            "created_at",
        )


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except FinanceError as exc:
        raise serializers.ValidationError(str(exc)) from exc
