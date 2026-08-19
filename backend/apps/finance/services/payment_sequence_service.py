"""Sequential payment rules for monthly / tranche fee groups."""

from __future__ import annotations

from decimal import Decimal

from apps.finance.models import SchoolFee, StudentFeeObligation
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.fee_structure_service import MONTH_LABELS_FR
from apps.secretariat.models import Enrollment


def payment_group_key(fee: SchoolFee) -> str:
    """Stable key to group sibling fees under one combobox entry."""
    category_code = fee.category.code if fee.category_id else ""
    if category_code in {"MINERVAL", "SCOLARITE"}:
        return "MINERVAL"
    if category_code == "FRAIS_ETAT":
        return "FRAIS_ETAT"
    if fee.group_key:
        return fee.group_key.strip().upper()
    return (fee.code or str(fee.pk)).strip().upper()


def payment_group_label(fee: SchoolFee) -> str:
    """Display name only (no month / tranche / amount)."""
    category_code = fee.category.code if fee.category_id else ""
    if category_code in {"MINERVAL", "SCOLARITE"}:
        return "Minerval"
    if category_code == "FRAIS_ETAT":
        return "Frais de l'État"
    if " — " in (fee.label or ""):
        return fee.label.split(" — ", 1)[0].strip()
    return (fee.label or "").strip() or (
        fee.category.name if fee.category_id else fee.code
    )


def payment_group_schedule_mode(fee: SchoolFee) -> str:
    category_code = fee.category.code if fee.category_id else ""
    if category_code in {"MINERVAL", "SCOLARITE"}:
        return SchoolFee.ScheduleMode.MONTHS
    if category_code == "FRAIS_ETAT":
        return SchoolFee.ScheduleMode.TRANCHES
    if fee.schedule_mode in SchoolFee.ScheduleMode.values:
        return fee.schedule_mode
    return SchoolFee.ScheduleMode.ONCE


def build_payable_fee_groups(fees: list[SchoolFee]) -> list[dict]:
    """
    Group payable SchoolFee rows for the two-step payment comboboxes.

    Each group: key, label, schedule_mode, periods[{id, label}].
    """
    groups: dict[str, dict] = {}
    for fee in fees:
        key = payment_group_key(fee)
        mode = payment_group_schedule_mode(fee)
        if key not in groups:
            groups[key] = {
                "key": key,
                "label": payment_group_label(fee),
                "schedule_mode": mode,
                "fees": [],
                "periods": [],
            }
        groups[key]["fees"].append(fee)
        groups[key]["periods"].append(
            {"id": fee.pk, "label": fee_period_short_label(fee)}
        )
        # Prefer non-ONCE mode if siblings disagree
        if mode != SchoolFee.ScheduleMode.ONCE:
            groups[key]["schedule_mode"] = mode

    return list(groups.values())


def _obligation_period_is_payable(obligation: StudentFeeObligation | None) -> bool:
    """True when the period may still receive a payment."""
    if obligation is None:
        return True
    if obligation.status in {
        StudentFeeObligation.Status.EXEMPTED,
        StudentFeeObligation.Status.CANCELLED,
        StudentFeeObligation.Status.PAID,
    }:
        return False
    return obligation.amount_remaining > 0


def _period_option_label(
    fee: SchoolFee,
    *,
    base_label: str,
    obligation: StudentFeeObligation | None,
) -> str:
    if obligation is None or obligation.amount_remaining <= 0:
        return base_label
    remaining = obligation.amount_remaining.quantize(Decimal("0.01"))
    currency = (fee.currency or "CDF").strip()
    if obligation.status == StudentFeeObligation.Status.PARTIAL:
        return f"{base_label} — reste {remaining} {currency}"
    return base_label


def build_payable_fee_groups_for_enrollment(
    *,
    enrollment: Enrollment,
    fees: list[SchoolFee],
) -> list[dict]:
    """
    Fee groups for the payment form: only periods still owed (unpaid or partial).

    Fully paid periods are omitted so accountants are not misled.
    """
    fee_ids = [fee.pk for fee in fees]
    obligations = {
        row.fee_id: row
        for row in StudentFeeObligation.objects.filter(
            enrollment=enrollment,
            fee_id__in=fee_ids,
        ).select_related("fee")
    }

    filtered: list[dict] = []
    for group in build_payable_fee_groups(fees):
        open_fees: list[SchoolFee] = []
        open_periods: list[dict] = []
        for fee in group["fees"]:
            obligation = obligations.get(fee.pk)
            if not _obligation_period_is_payable(obligation):
                continue
            base_label = fee_period_short_label(fee)
            open_fees.append(fee)
            period_payload = {
                "id": fee.pk,
                "label": _period_option_label(
                    fee,
                    base_label=base_label,
                    obligation=obligation,
                ),
            }
            if obligation is not None:
                period_payload["status"] = obligation.status
                period_payload["amount_remaining"] = str(
                    obligation.amount_remaining.quantize(Decimal("0.01"))
                )
            open_periods.append(period_payload)

        if not open_fees:
            continue

        filtered.append(
            {
                **group,
                "fees": open_fees,
                "periods": open_periods,
            }
        )
    return filtered


def fee_period_short_label(fee: SchoolFee) -> str:
    """Short combo label: Septembre / 1ère tranche / Inscription…"""
    category_code = fee.category.code if fee.category_id else ""
    if category_code in {"MINERVAL", "SCOLARITE"} or fee.schedule_mode == SchoolFee.ScheduleMode.MONTHS:
        if fee.due_date:
            return MONTH_LABELS_FR.get(fee.due_date.month, fee.label)
        if " — " in fee.label:
            tail = fee.label.split(" — ", 1)[1].strip()
            # "Septembre 2025" → "Septembre"
            return tail.split(" ")[0] if tail else fee.label
        return fee.label
    if category_code == "FRAIS_ETAT" or fee.schedule_mode == SchoolFee.ScheduleMode.TRANCHES:
        if fee.period_index == 1:
            return "1ère tranche"
        if fee.period_index:
            return f"{fee.period_index}ème tranche"
        # Structural état labels are already short ("1ère tranche")
        label = (fee.label or "").strip()
        if " — " in label:
            return label.split(" — ", 1)[1].strip()
        return label
    if fee.schedule_mode == SchoolFee.ScheduleMode.MONTHS:
        label = (fee.label or "").strip()
        if " — " in label:
            tail = label.split(" — ", 1)[1].strip()
            return tail.split(" ")[0] if tail else label
        return label.split(" ")[0] if label else fee.code
    if " — " in fee.label:
        return fee.label.split(" — ", 1)[0].strip()
    return fee.label


def sequence_queryset(*, fee: SchoolFee):
    """Sibling fees that must be paid in order with this fee."""
    year_id = fee.academic_year_id
    category_code = fee.category.code if fee.category_id else ""
    qs = SchoolFee.objects.filter(
        academic_year_id=year_id,
        status=SchoolFee.Status.APPROVED,
        is_active=True,
        is_archived=False,
    ).select_related("category")

    if fee.group_key:
        return qs.filter(group_key__iexact=fee.group_key).order_by(
            "period_index", "due_date", "code"
        )
    if category_code in {"MINERVAL", "SCOLARITE"}:
        return qs.filter(category__code__in=["MINERVAL", "SCOLARITE"]).order_by(
            "due_date", "period_index", "code"
        )
    if category_code == "FRAIS_ETAT":
        return qs.filter(category__code="FRAIS_ETAT").order_by(
            "period_index", "code"
        )
    if fee.schedule_mode in {
        SchoolFee.ScheduleMode.MONTHS,
        SchoolFee.ScheduleMode.TRANCHES,
    }:
        return qs.filter(code=fee.code).order_by("period_index", "due_date", "code")
    return qs.filter(pk=fee.pk)


def resolve_sequential_obligation(
    *,
    enrollment: Enrollment,
    selected_fee: SchoolFee,
) -> tuple[StudentFeeObligation, bool]:
    """
    Return the obligation that must receive the payment.

    For ordered groups (minerval / état / tranches / mois), always target the
    earliest unpaid period. Returns (obligation, redirected_from_selection).
    """
    siblings = list(sequence_queryset(fee=selected_fee))
    sibling_ids = [f.pk for f in siblings] or [selected_fee.pk]

    obligations = list(
        StudentFeeObligation.objects.filter(
            enrollment=enrollment,
            fee_id__in=sibling_ids,
        )
        .exclude(
            status__in=[
                StudentFeeObligation.Status.EXEMPTED,
                StudentFeeObligation.Status.CANCELLED,
            ]
        )
        .select_related("fee", "fee__category")
    )
    by_fee = {o.fee_id: o for o in obligations}

    ordered: list[StudentFeeObligation] = []
    for fee in siblings:
        obligation = by_fee.get(fee.pk)
        if obligation is not None:
            ordered.append(obligation)

    if not ordered:
        raise FinanceError(
            f"Aucune dette ouverte pour « {fee_period_short_label(selected_fee)} » "
            "sur cet élève."
        )

    first_open = None
    for obligation in ordered:
        if (
            obligation.status != StudentFeeObligation.Status.PAID
            and obligation.amount_remaining > 0
        ):
            first_open = obligation
            break

    if first_open is None:
        raise FinanceError("Toutes les périodes de ce frais sont déjà soldées.")

    redirected = first_open.fee_id != selected_fee.pk
    return first_open, redirected
