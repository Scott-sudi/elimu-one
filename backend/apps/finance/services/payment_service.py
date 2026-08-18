"""Payment recording, cancellation and receipt number generation."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.finance.models import (
    Payment,
    PaymentAllocation,
    ReceiptSequence,
    StudentFeeObligation,
)
from apps.finance.services import audit_finance_action
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.obligation_service import recalculate_obligation
from apps.secretariat.models import AcademicYear, Enrollment


def _sanitize_year_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", (label or "").strip().upper())
    return cleaned or "YEAR"


def generate_receipt_number(*, academic_year: AcademicYear) -> str:
    """Generate the next receipt number for an academic year (race-safe)."""
    sequence, _ = ReceiptSequence.objects.get_or_create(
        academic_year=academic_year,
        defaults={"last_value": 0},
    )
    sequence = ReceiptSequence.objects.select_for_update().get(pk=sequence.pk)
    sequence.last_value += 1
    sequence.save(update_fields=["last_value", "updated_at"])
    year_part = _sanitize_year_label(academic_year.label)
    return f"REC-{year_part}-{sequence.last_value:06d}"


def _payment_snapshot(payment: Payment) -> dict:
    return {
        "public_id": str(payment.public_id),
        "receipt_number": payment.receipt_number,
        "amount_total": str(payment.amount_total),
        "currency": payment.currency,
        "status": payment.status,
        "payment_method": payment.payment_method,
        "payment_date": payment.payment_date.isoformat() if payment.payment_date else "",
    }


def _validate_allocations(
    *,
    enrollment: Enrollment,
    amount_total: Decimal,
    allocations: Iterable[dict],
) -> list[tuple[StudentFeeObligation, Decimal]]:
    prepared: list[tuple[StudentFeeObligation, Decimal]] = []
    seen_obligation_ids: set[int] = set()
    allocation_sum = Decimal("0.00")

    for item in allocations:
        obligation = item.get("obligation")
        amount = item.get("amount")
        if obligation is None:
            raise FinanceError("Chaque allocation doit cibler une obligation.")
        if not isinstance(obligation, StudentFeeObligation):
            try:
                obligation = StudentFeeObligation.objects.select_related("fee").get(
                    pk=obligation
                )
            except (StudentFeeObligation.DoesNotExist, TypeError, ValueError) as exc:
                raise FinanceError("Obligation de frais introuvable.") from exc

        if obligation.pk in seen_obligation_ids:
            raise FinanceError(
                "Une même obligation ne peut apparaître qu'une fois dans les allocations."
            )
        seen_obligation_ids.add(obligation.pk)

        if obligation.enrollment_id != enrollment.pk:
            raise FinanceError(
                "Les allocations doivent concerner l'inscription du paiement."
            )
        if obligation.status in {
            StudentFeeObligation.Status.EXEMPTED,
            StudentFeeObligation.Status.CANCELLED,
            StudentFeeObligation.Status.PAID,
        }:
            raise FinanceError(
                f"L'obligation « {obligation.fee.label} » n'accepte plus de paiement."
            )

        try:
            amount_value = Decimal(str(amount)).quantize(Decimal("0.01"))
        except Exception as exc:
            raise FinanceError("Montant d'allocation invalide.") from exc
        if amount_value <= 0:
            raise FinanceError("Chaque allocation doit être supérieure à zéro.")

        remaining = (obligation.amount_due - obligation.amount_paid).quantize(
            Decimal("0.01")
        )
        if amount_value > remaining:
            raise FinanceError(
                f"Surpaiement interdit pour « {obligation.fee.label} » "
                f"(reste dû : {remaining})."
            )
        if not obligation.fee.allow_partial and amount_value < remaining:
            raise FinanceError(
                f"Le frais « {obligation.fee.label} » n'autorise pas le paiement partiel."
            )

        prepared.append((obligation, amount_value))
        allocation_sum += amount_value

    if not prepared:
        raise FinanceError("Au moins une allocation est obligatoire.")
    if allocation_sum != amount_total:
        raise FinanceError(
            "La somme des allocations doit être égale au montant total du paiement."
        )
    return prepared


@transaction.atomic
def record_payment(
    *,
    enrollment: Enrollment,
    amount_total,
    allocations: Iterable[dict],
    payment_date=None,
    currency: str = "CDF",
    payment_method: str = Payment.PaymentMethod.CASH,
    transaction_reference: str = "",
    payer_name: str = "",
    payer_phone: str = "",
    observation: str = "",
    actor=None,
    request=None,
) -> Payment:
    """Record a payment with allocations and update obligation balances."""
    enrollment = (
        Enrollment.objects.select_for_update()
        .select_related("student", "academic_year", "school_class")
        .get(pk=enrollment.pk)
    )
    if enrollment.status != Enrollment.Status.VALIDATED:
        raise FinanceError(
            "Seule une inscription validée peut recevoir un paiement."
        )
    if enrollment.academic_year.is_closed:
        raise FinanceError("Impossible d'enregistrer un paiement sur une année clôturée.")

    try:
        amount_value = Decimal(str(amount_total)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise FinanceError("Montant total invalide.") from exc
    if amount_value <= 0:
        raise FinanceError("Le montant total doit être supérieur à zéro.")

    if payment_method not in Payment.PaymentMethod.values:
        raise FinanceError("Mode de paiement invalide.")

    # Lock obligations involved before validating remaining balances.
    obligation_ids = []
    for item in allocations:
        obligation = item.get("obligation")
        if isinstance(obligation, StudentFeeObligation):
            obligation_ids.append(obligation.pk)
        elif obligation is not None:
            obligation_ids.append(int(obligation))
    if obligation_ids:
        list(
            StudentFeeObligation.objects.select_for_update()
            .select_related("fee")
            .filter(pk__in=obligation_ids)
            .order_by("pk")
        )

    prepared = _validate_allocations(
        enrollment=enrollment,
        amount_total=amount_value,
        allocations=allocations,
    )

    receipt_number = generate_receipt_number(academic_year=enrollment.academic_year)
    payment = Payment.objects.create(
        academic_year=enrollment.academic_year,
        enrollment=enrollment,
        student_id=enrollment.student_id,
        receipt_number=receipt_number,
        payment_date=payment_date or timezone.localdate(),
        amount_total=amount_value,
        currency=(currency or "CDF").strip().upper() or "CDF",
        payment_method=payment_method,
        transaction_reference=(transaction_reference or "").strip(),
        payer_name=(payer_name or "").strip(),
        payer_phone=(payer_phone or "").strip(),
        observation=(observation or "").strip(),
        status=Payment.Status.VALID,
        recorded_by=actor,
    )
    PaymentAllocation.objects.bulk_create(
        [
            PaymentAllocation(
                payment=payment,
                obligation=obligation,
                amount=amount,
            )
            for obligation, amount in prepared
        ]
    )
    for obligation, _amount in prepared:
        recalculate_obligation(obligation)

    audit_finance_action(
        action=AuditLog.Action.PAYMENT_RECORDED,
        instance=payment,
        description=(
            f"Paiement {payment.receipt_number} de {payment.amount_total} "
            f"{payment.currency} pour {enrollment.enrollment_number}"
        ),
        actor=actor,
        request=request,
        new_values=_payment_snapshot(payment),
    )

    try:
        from apps.api.parents_push import notify_guardians_of_payment

        payment_id = payment.pk

        def _push_payment() -> None:
            from apps.finance.models import Payment as P

            pay = (
                P.objects.select_related("student", "enrollment", "enrollment__student")
                .filter(pk=payment_id)
                .first()
            )
            if pay is not None:
                notify_guardians_of_payment(payment=pay)

        transaction.on_commit(_push_payment)
    except Exception:
        pass

    return payment


@transaction.atomic
def cancel_payment(
    *,
    payment: Payment,
    reason: str,
    actor=None,
    request=None,
) -> Payment:
    """Cancel a valid payment and reverse its effect on obligations."""
    payment = (
        Payment.objects.select_for_update()
        .prefetch_related("allocations__obligation")
        .get(pk=payment.pk)
    )
    if payment.status != Payment.Status.VALID:
        raise FinanceError("Seuls les paiements validés peuvent être annulés.")
    reason = (reason or "").strip()
    if not reason:
        raise FinanceError("Le motif d'annulation est obligatoire.")

    old_values = _payment_snapshot(payment)
    obligation_ids = list(
        payment.allocations.values_list("obligation_id", flat=True)
    )
    if obligation_ids:
        list(
            StudentFeeObligation.objects.select_for_update()
            .filter(pk__in=obligation_ids)
            .order_by("pk")
        )

    payment.status = Payment.Status.CANCELLED
    payment.cancelled_by = actor
    payment.cancelled_at = timezone.now()
    payment.cancellation_reason = reason
    payment.save(
        update_fields=[
            "status",
            "cancelled_by",
            "cancelled_at",
            "cancellation_reason",
            "updated_at",
        ]
    )

    for obligation in StudentFeeObligation.objects.filter(pk__in=obligation_ids):
        recalculate_obligation(obligation)

    audit_finance_action(
        action=AuditLog.Action.PAYMENT_CANCELLED,
        instance=payment,
        description=f"Annulation du paiement {payment.receipt_number}",
        actor=actor,
        request=request,
        old_values=old_values,
        new_values=_payment_snapshot(payment),
    )
    try:
        from apps.api.parents_push import notify_guardians_of_payment

        payment_id = payment.pk

        def _push_cancelled() -> None:
            from apps.finance.models import Payment as P

            pay = (
                P.objects.select_related("student", "enrollment", "enrollment__student")
                .filter(pk=payment_id)
                .first()
            )
            if pay is not None:
                notify_guardians_of_payment(payment=pay, cancelled=True)

        transaction.on_commit(_push_cancelled)
    except Exception:
        pass
    return payment
