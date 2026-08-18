"""Administration registration for finance models."""

from __future__ import annotations

from django.contrib import admin

from apps.finance.models import (
    FeeApprovalHistory,
    FeeCategory,
    FeeRevisionRequest,
    FeeTarget,
    Payment,
    PaymentAllocation,
    ReceiptSequence,
    SchoolFee,
    StudentFeeObligation,
)


@admin.register(FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    list_per_page = 50


@admin.register(SchoolFee)
class SchoolFeeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "label",
        "academic_year",
        "category",
        "amount",
        "currency",
        "status",
        "is_active",
        "is_archived",
    )
    list_filter = ("status", "academic_year", "is_active", "is_archived", "category")
    search_fields = ("code", "label")
    list_per_page = 50


@admin.register(FeeTarget)
class FeeTargetAdmin(admin.ModelAdmin):
    list_display = ("fee", "school_class", "level", "section", "option")
    list_filter = ("fee__academic_year",)
    search_fields = ("fee__code", "fee__label")
    list_per_page = 50


@admin.register(FeeApprovalHistory)
class FeeApprovalHistoryAdmin(admin.ModelAdmin):
    list_display = ("fee", "action", "previous_status", "new_status", "actor", "created_at")
    list_filter = ("action",)
    search_fields = ("fee__code", "comment")
    list_per_page = 50
    readonly_fields = (
        "fee",
        "action",
        "previous_status",
        "new_status",
        "comment",
        "actor",
        "created_at",
        "updated_at",
        "public_id",
    )


@admin.register(FeeRevisionRequest)
class FeeRevisionRequestAdmin(admin.ModelAdmin):
    list_display = ("fee", "requested_amount", "status", "requested_by", "created_at")
    list_filter = ("status",)
    search_fields = ("fee__code", "reason")
    list_per_page = 50


@admin.register(StudentFeeObligation)
class StudentFeeObligationAdmin(admin.ModelAdmin):
    list_display = (
        "fee",
        "student",
        "enrollment",
        "amount_due",
        "amount_paid",
        "status",
    )
    list_filter = ("status", "fee__academic_year")
    search_fields = (
        "student__matricule",
        "student__nom",
        "enrollment__enrollment_number",
        "fee__code",
    )
    list_per_page = 50


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_number",
        "student",
        "amount_total",
        "currency",
        "payment_date",
        "payment_method",
        "status",
    )
    list_filter = ("status", "payment_method", "academic_year")
    search_fields = (
        "receipt_number",
        "student__matricule",
        "enrollment__enrollment_number",
        "payer_name",
    )
    list_per_page = 50


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ("payment", "obligation", "amount")
    search_fields = ("payment__receipt_number",)
    list_per_page = 50


@admin.register(ReceiptSequence)
class ReceiptSequenceAdmin(admin.ModelAdmin):
    list_display = ("academic_year", "last_value")
    list_per_page = 50
