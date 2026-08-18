"""Fee approval / rejection services (secretary side)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.finance.models import FeeApprovalHistory, SchoolFee
from apps.finance.services import audit_finance_action
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.fee_service import _fee_snapshot, _record_history, resolve_target_classes
from apps.finance.services.obligation_service import create_obligations_for_fee


@transaction.atomic
def approve_fee(
    *,
    fee: SchoolFee,
    actor=None,
    request=None,
    comment: str = "",
) -> SchoolFee:
    """Approve a pending fee and create obligations for validated enrollments."""
    fee = SchoolFee.objects.select_for_update().select_related("academic_year").get(
        pk=fee.pk
    )
    if fee.status != SchoolFee.Status.PENDING:
        raise FinanceError("Seuls les frais en attente peuvent être approuvés.")
    if fee.is_archived or not fee.is_active:
        raise FinanceError("Ce frais ne peut pas être approuvé.")
    if fee.academic_year.is_closed:
        raise FinanceError("Impossible d'approuver un frais sur une année clôturée.")
    if fee.application_type != SchoolFee.ApplicationType.ALL_CLASSES:
        if not resolve_target_classes(fee).exists():
            raise FinanceError(
                "Aucune classe active ne correspond aux cibles de ce frais."
            )

    previous_status = fee.status
    old_values = _fee_snapshot(fee)
    fee.status = SchoolFee.Status.APPROVED
    fee.reviewed_by = actor
    fee.reviewed_at = timezone.now()
    fee.rejection_reason = ""
    fee.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_at",
        ]
    )
    create_obligations_for_fee(fee=fee)
    _record_history(
        fee=fee,
        action=FeeApprovalHistory.Action.APPROVED,
        previous_status=previous_status,
        new_status=fee.status,
        actor=actor,
        comment=(comment or "").strip(),
    )
    audit_finance_action(
        action=AuditLog.Action.FEE_APPROVED,
        instance=fee,
        description=f"Approbation du frais {fee.code}",
        actor=actor,
        request=request,
        old_values=old_values,
        new_values=_fee_snapshot(fee),
    )
    return fee


@transaction.atomic
def reject_fee(
    *,
    fee: SchoolFee,
    reason: str,
    actor=None,
    request=None,
) -> SchoolFee:
    """Reject a pending fee with a mandatory reason."""
    fee = SchoolFee.objects.select_for_update().get(pk=fee.pk)
    if fee.status != SchoolFee.Status.PENDING:
        raise FinanceError("Seuls les frais en attente peuvent être rejetés.")
    reason = (reason or "").strip()
    if not reason:
        raise FinanceError("Le motif de rejet est obligatoire.")

    previous_status = fee.status
    old_values = _fee_snapshot(fee)
    fee.status = SchoolFee.Status.REJECTED
    fee.reviewed_by = actor
    fee.reviewed_at = timezone.now()
    fee.rejection_reason = reason
    fee.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_at",
        ]
    )
    _record_history(
        fee=fee,
        action=FeeApprovalHistory.Action.REJECTED,
        previous_status=previous_status,
        new_status=fee.status,
        actor=actor,
        comment=reason,
    )
    audit_finance_action(
        action=AuditLog.Action.FEE_REJECTED,
        instance=fee,
        description=f"Rejet du frais {fee.code}",
        actor=actor,
        request=request,
        old_values=old_values,
        new_values=_fee_snapshot(fee),
    )
    return fee
