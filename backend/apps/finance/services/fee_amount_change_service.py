"""Submit / approve fee amount changes from class board column headers."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.finance.models import (
    FeeAmountChangeRequest,
    FeeClassAmount,
    SchoolFee,
    StudentFeeObligation,
)
from apps.finance.services import audit_finance_action
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.obligation_service import recalculate_obligation
from apps.secretariat.models import SchoolClass


def effective_fee_amount(*, fee: SchoolFee, school_class: SchoolClass | None) -> Decimal:
    """Return the amount that applies to a class (override or base fee amount)."""
    if school_class is not None:
        override = (
            FeeClassAmount.objects.filter(fee_id=fee.pk, school_class_id=school_class.pk)
            .only("amount")
            .first()
        )
        if override is not None:
            return Decimal(override.amount).quantize(Decimal("0.01"))
    return Decimal(fee.amount).quantize(Decimal("0.01"))


def _parse_amount(value) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise FinanceError("Montant invalide.") from exc
    if amount < Decimal("0.01"):
        raise FinanceError("Le montant doit être supérieur à zéro.")
    return amount


def resolve_change_target_classes(
    *,
    request: FeeAmountChangeRequest,
) -> list[SchoolClass]:
    """Classes that will receive the new amount when the request is approved."""
    if request.scope == FeeAmountChangeRequest.Scope.ALL_CLASSES:
        return list(
            SchoolClass.objects.filter(
                academic_year_id=request.fee.academic_year_id,
                is_active=True,
            ).order_by("name")
        )
    if request.scope == FeeAmountChangeRequest.Scope.CURRENT_CLASS:
        return [request.origin_class]
    return list(request.target_classes.filter(is_active=True).order_by("name"))


@transaction.atomic
def submit_amount_change(
    *,
    fee: SchoolFee,
    origin_class: SchoolClass,
    new_amount,
    scope: str,
    target_classes: list[SchoolClass] | None = None,
    comment: str = "",
    actor=None,
    request=None,
) -> FeeAmountChangeRequest:
    """Accountant submits a pending amount change for a fee period column."""
    fee = SchoolFee.objects.select_related("academic_year").get(pk=fee.pk)
    if fee.status != SchoolFee.Status.APPROVED or not fee.is_active or fee.is_archived:
        raise FinanceError("Seuls les frais approuvés peuvent être modifiés.")
    if fee.academic_year.is_closed:
        raise FinanceError("Année scolaire clôturée — modification impossible.")
    if origin_class.academic_year_id != fee.academic_year_id:
        raise FinanceError("La classe n'appartient pas à l'année du frais.")

    amount = _parse_amount(new_amount)
    if scope not in FeeAmountChangeRequest.Scope.values:
        raise FinanceError("Portée de modification invalide.")

    target_classes = list(target_classes or [])
    if scope == FeeAmountChangeRequest.Scope.CURRENT_CLASS:
        target_classes = [origin_class]
    elif scope == FeeAmountChangeRequest.Scope.SELECTED_CLASSES:
        if not target_classes:
            raise FinanceError("Sélectionnez au moins une classe.")
        for school_class in target_classes:
            if school_class.academic_year_id != fee.academic_year_id:
                raise FinanceError(
                    f"La classe {school_class} n'appartient pas à l'année scolaire."
                )
    else:
        target_classes = []

    if FeeAmountChangeRequest.objects.filter(
        fee=fee,
        status=FeeAmountChangeRequest.Status.PENDING,
    ).exists():
        raise FinanceError(
            "Une demande de modification est déjà en attente pour cette période."
        )

    previous = effective_fee_amount(fee=fee, school_class=origin_class)
    change = FeeAmountChangeRequest.objects.create(
        fee=fee,
        new_amount=amount,
        previous_base_amount=previous,
        scope=scope,
        origin_class=origin_class,
        status=FeeAmountChangeRequest.Status.PENDING,
        comment=(comment or "").strip(),
        requested_by=actor,
        submitted_at=timezone.now(),
    )
    if scope != FeeAmountChangeRequest.Scope.ALL_CLASSES:
        change.target_classes.set(target_classes)

    audit_finance_action(
        action=AuditLog.Action.FEE_UPDATED,
        instance=fee,
        description=(
            f"Demande de modification du montant de {fee.code} "
            f"({previous} → {amount}, {change.get_scope_display()})"
        ),
        actor=actor,
        request=request,
        old_values={"amount": str(previous)},
        new_values={"amount": str(amount), "scope": scope},
    )
    return change


def sync_obligation_amounts(
    *,
    fee: SchoolFee,
    school_classes: list[SchoolClass] | None = None,
) -> int:
    """
    Refresh amount_due from effective amounts and recalculate statuses.

    If school_classes is None, sync all obligations of the fee.
    """
    qs = StudentFeeObligation.objects.filter(fee=fee).exclude(
        status__in=[
            StudentFeeObligation.Status.EXEMPTED,
            StudentFeeObligation.Status.CANCELLED,
        ]
    ).select_related("enrollment__school_class")
    if school_classes is not None:
        class_ids = [c.pk for c in school_classes]
        qs = qs.filter(enrollment__school_class_id__in=class_ids)

    updated = 0
    for obligation in qs:
        school_class = obligation.enrollment.school_class
        new_due = effective_fee_amount(fee=fee, school_class=school_class)
        if obligation.amount_due != new_due:
            obligation.amount_due = new_due
            obligation.save(update_fields=["amount_due", "updated_at"])
            updated += 1
        recalculate_obligation(obligation)
    return updated


@transaction.atomic
def approve_amount_change(
    *,
    change: FeeAmountChangeRequest,
    actor=None,
    request=None,
    comment: str = "",
) -> FeeAmountChangeRequest:
    """Secretary approves; apply amount and sync obligations."""
    change = (
        FeeAmountChangeRequest.objects.select_for_update()
        .select_related("fee", "fee__academic_year", "origin_class")
        .prefetch_related("target_classes")
        .get(pk=change.pk)
    )
    if change.status != FeeAmountChangeRequest.Status.PENDING:
        raise FinanceError("Seules les demandes en attente peuvent être approuvées.")
    fee = change.fee
    if fee.academic_year.is_closed:
        raise FinanceError("Année scolaire clôturée — approbation impossible.")

    amount = Decimal(change.new_amount).quantize(Decimal("0.01"))
    classes = resolve_change_target_classes(request=change)

    if change.scope == FeeAmountChangeRequest.Scope.ALL_CLASSES:
        fee.amount = amount
        fee.save(update_fields=["amount", "updated_at"])
        FeeClassAmount.objects.filter(fee=fee).delete()
        sync_obligation_amounts(fee=fee, school_classes=None)
    else:
        for school_class in classes:
            FeeClassAmount.objects.update_or_create(
                fee=fee,
                school_class=school_class,
                defaults={"amount": amount},
            )
        sync_obligation_amounts(fee=fee, school_classes=classes)

    change.status = FeeAmountChangeRequest.Status.APPROVED
    change.reviewed_by = actor
    change.reviewed_at = timezone.now()
    if (comment or "").strip():
        change.comment = f"{change.comment}\n{comment.strip()}".strip()
    change.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "comment",
            "updated_at",
        ]
    )

    audit_finance_action(
        action=AuditLog.Action.FEE_APPROVED,
        instance=fee,
        description=(
            f"Approbation modification montant {fee.code} → {amount} "
            f"({change.get_scope_display()})"
        ),
        actor=actor,
        request=request,
        new_values={"amount": str(amount), "scope": change.scope},
    )
    return change


@transaction.atomic
def reject_amount_change(
    *,
    change: FeeAmountChangeRequest,
    reason: str,
    actor=None,
    request=None,
) -> FeeAmountChangeRequest:
    """Secretary rejects a pending amount change."""
    change = FeeAmountChangeRequest.objects.select_for_update().get(pk=change.pk)
    if change.status != FeeAmountChangeRequest.Status.PENDING:
        raise FinanceError("Seules les demandes en attente peuvent être rejetées.")
    reason = (reason or "").strip()
    if not reason:
        raise FinanceError("Le motif de rejet est obligatoire.")

    change.status = FeeAmountChangeRequest.Status.REJECTED
    change.rejection_reason = reason
    change.reviewed_by = actor
    change.reviewed_at = timezone.now()
    change.save(
        update_fields=[
            "status",
            "rejection_reason",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )
    audit_finance_action(
        action=AuditLog.Action.FEE_REJECTED,
        instance=change.fee,
        description=f"Rejet modification montant {change.fee.code}",
        actor=actor,
        request=request,
        new_values={"reason": reason},
    )
    return change
