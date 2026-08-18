"""Financial querysets for BI — money as Decimal, cancelled payments excluded."""

from __future__ import annotations

from django.db.models import QuerySet

from apps.bi.filters import BiFilters, apply_class_structure_filters, apply_date_range
from apps.finance.models import Payment, StudentFeeObligation
from apps.secretariat.models import AcademicYear


def obligations_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
    *,
    exclude_cancelled: bool = True,
) -> QuerySet[StudentFeeObligation]:
    qs = (
        StudentFeeObligation.objects.filter(fee__academic_year=academic_year)
        .select_related(
            "fee",
            "fee__category",
            "enrollment",
            "enrollment__school_class",
            "student",
        )
    )
    if exclude_cancelled:
        qs = qs.exclude(status=StudentFeeObligation.Status.CANCELLED)
    filters = filters or BiFilters()
    qs = apply_class_structure_filters(qs, filters, class_prefix="enrollment__school_class")
    if filters.fee_id:
        qs = qs.filter(fee_id=filters.fee_id)
    if filters.gender:
        qs = qs.filter(student__sexe=filters.gender)
    return qs


def valid_payments_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> QuerySet[Payment]:
    """Payments with status=VALIDE only — ANNULE never counted as collected."""
    qs = Payment.objects.filter(
        academic_year=academic_year,
        status=Payment.Status.VALID,
    ).select_related(
        "enrollment",
        "enrollment__school_class",
        "student",
    )
    filters = filters or BiFilters()
    qs = apply_class_structure_filters(qs, filters, class_prefix="enrollment__school_class")
    qs = apply_date_range(qs, filters, field="payment_date")
    if filters.fee_id:
        qs = qs.filter(allocations__obligation__fee_id=filters.fee_id).distinct()
    if filters.payment_method:
        qs = qs.filter(payment_method=filters.payment_method)
    if filters.gender:
        qs = qs.filter(student__sexe=filters.gender)
    return qs


def payments_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
    *,
    include_cancelled: bool = False,
) -> QuerySet[Payment]:
    qs = Payment.objects.filter(academic_year=academic_year).select_related(
        "enrollment",
        "enrollment__school_class",
        "student",
    )
    filters = filters or BiFilters()
    if filters.payment_status:
        qs = qs.filter(status=filters.payment_status)
    elif not include_cancelled:
        qs = qs.filter(status=Payment.Status.VALID)
    qs = apply_class_structure_filters(qs, filters, class_prefix="enrollment__school_class")
    qs = apply_date_range(qs, filters, field="payment_date")
    if filters.fee_id:
        qs = qs.filter(allocations__obligation__fee_id=filters.fee_id).distinct()
    if filters.payment_method:
        qs = qs.filter(payment_method=filters.payment_method)
    if filters.gender:
        qs = qs.filter(student__sexe=filters.gender)
    return qs


def cancelled_payments_qs(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> QuerySet[Payment]:
    qs = Payment.objects.filter(
        academic_year=academic_year,
        status=Payment.Status.CANCELLED,
    )
    filters = filters or BiFilters()
    qs = apply_class_structure_filters(qs, filters, class_prefix="enrollment__school_class")
    qs = apply_date_range(qs, filters, field="payment_date")
    return qs
