"""Student fee obligation creation and recalculation services."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from apps.finance.models import Payment, SchoolFee, StudentFeeObligation
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.fee_service import fee_applies_to_class, resolve_target_classes
from apps.secretariat.models import Enrollment


def recalculate_obligation(obligation: StudentFeeObligation) -> StudentFeeObligation:
    """Recompute amount_paid and status from valid payment allocations."""
    total_paid = obligation.allocations.filter(
        payment__status=Payment.Status.VALID,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_paid = Decimal(total_paid).quantize(Decimal("0.01"))
    obligation.amount_paid = total_paid

    if obligation.status not in {
        StudentFeeObligation.Status.EXEMPTED,
        StudentFeeObligation.Status.CANCELLED,
    }:
        if total_paid <= 0:
            obligation.status = StudentFeeObligation.Status.UNPAID
        elif total_paid >= obligation.amount_due:
            obligation.status = StudentFeeObligation.Status.PAID
        else:
            obligation.status = StudentFeeObligation.Status.PARTIAL

    obligation.save(update_fields=["amount_paid", "status", "updated_at"])
    return obligation


def _create_obligation_if_missing(
    *,
    fee: SchoolFee,
    enrollment: Enrollment,
) -> StudentFeeObligation | None:
    if StudentFeeObligation.objects.filter(fee=fee, enrollment=enrollment).exists():
        return None
    from apps.finance.services.fee_amount_change_service import effective_fee_amount

    return StudentFeeObligation.objects.create(
        fee=fee,
        enrollment=enrollment,
        student_id=enrollment.student_id,
        amount_due=effective_fee_amount(fee=fee, school_class=enrollment.school_class),
        amount_paid=Decimal("0.00"),
        status=StudentFeeObligation.Status.UNPAID,
    )


@transaction.atomic
def create_obligations_for_fee(*, fee: SchoolFee) -> list[StudentFeeObligation]:
    """Create obligations for all validated enrollments in the fee's target classes."""
    if fee.status != SchoolFee.Status.APPROVED:
        raise FinanceError(
            "Les obligations ne peuvent être créées que pour un frais approuvé."
        )

    target_classes = resolve_target_classes(fee)
    enrollments = (
        Enrollment.objects.filter(
            academic_year_id=fee.academic_year_id,
            school_class_id__in=target_classes.values_list("pk", flat=True),
            status=Enrollment.Status.VALIDATED,
        )
        .select_related("student", "school_class")
        .order_by("pk")
    )

    created: list[StudentFeeObligation] = []
    for enrollment in enrollments:
        obligation = _create_obligation_if_missing(fee=fee, enrollment=enrollment)
        if obligation is not None:
            created.append(obligation)
    return created


@transaction.atomic
def create_obligations_for_enrollment(
    *,
    enrollment: Enrollment,
) -> list[StudentFeeObligation]:
    """Create missing obligations for all approved active fees applying to the class."""
    enrollment = Enrollment.objects.select_related("school_class", "student").get(
        pk=enrollment.pk
    )
    if enrollment.status != Enrollment.Status.VALIDATED:
        return []

    fees = (
        SchoolFee.objects.filter(
            academic_year_id=enrollment.academic_year_id,
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
        )
        .select_related("category")
        .prefetch_related("targets")
        .order_by("pk")
    )

    created: list[StudentFeeObligation] = []
    for fee in fees:
        if not fee_applies_to_class(fee, enrollment.school_class):
            continue
        obligation = _create_obligation_if_missing(fee=fee, enrollment=enrollment)
        if obligation is not None:
            created.append(obligation)
    return created


@transaction.atomic
def sync_obligations_after_transfer(
    *,
    enrollment: Enrollment,
) -> list[StudentFeeObligation]:
    """Create obligations for fees that apply to the new class but are still missing."""
    return create_obligations_for_enrollment(enrollment=enrollment)
