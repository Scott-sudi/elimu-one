"""Shared filter helpers for finance list pages (arrears, payments)."""

from __future__ import annotations

from apps.finance.models import SchoolFee
from apps.finance.services.payment_sequence_service import build_payable_fee_groups
from apps.secretariat.models import AcademicYear, Option, SchoolClass


def year_approved_fees(year: AcademicYear) -> list[SchoolFee]:
    return list(
        SchoolFee.objects.filter(
            academic_year=year,
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
        )
        .select_related("category")
        .order_by("category__order", "group_key", "period_index", "due_date", "code")
    )


def fee_filter_groups_payload(fees: list[SchoolFee]) -> list[dict]:
    groups = build_payable_fee_groups(fees)
    payload = []
    for group in groups:
        payload.append(
            {
                "key": group["key"],
                "label": group["label"],
                "schedule_mode": group["schedule_mode"],
                "periods": [
                    {
                        "id": str(fee.public_id),
                        "label": period["label"],
                    }
                    for fee, period in zip(group["fees"], group["periods"])
                ],
            }
        )
    return payload


def level_filter_payload(year: AcademicYear) -> list[dict]:
    """Levels used this year, with option public_ids that open classes on them."""
    classes = (
        SchoolClass.objects.filter(academic_year=year, is_active=True)
        .select_related("level", "option")
        .order_by("level__order", "level__name")
    )
    by_level: dict[str, dict] = {}
    for school_class in classes:
        level = school_class.level
        if level is None:
            continue
        key = str(level.public_id)
        if key not in by_level:
            by_level[key] = {
                "id": key,
                "label": level.name,
                "order": level.order,
                "option_ids": set(),
            }
        if school_class.option_id:
            by_level[key]["option_ids"].add(str(school_class.option.public_id))
        else:
            by_level[key]["option_ids"].add("")

    levels = sorted(by_level.values(), key=lambda item: (item["order"], item["label"]))
    for item in levels:
        item["option_ids"] = sorted(item["option_ids"])
    return levels


def active_options():
    return Option.objects.filter(is_active=True).order_by("name")


def resolve_fee_filter_ids(*, year: AcademicYear, frais: str, periode: str) -> list[int] | None:
    """
    Return fee PKs matching frais/periode filters, or None if no fee filter.
    Empty list means an unknown filter that should match nothing.
    """
    frais_key = (frais or "").strip().upper()
    periode_id = (periode or "").strip()
    if not frais_key and not periode_id:
        return None

    fees = year_approved_fees(year)
    fees_by_public = {str(f.public_id): f for f in fees}
    fee_groups = {g["key"]: g for g in build_payable_fee_groups(fees)}

    if periode_id:
        fee = fees_by_public.get(periode_id)
        return [fee.pk] if fee else []

    if frais_key in fee_groups:
        return [fee.pk for fee in fee_groups[frais_key]["fees"]]
    return []


def list_filter_context(request, *, year: AcademicYear) -> dict:
    fees = year_approved_fees(year)
    fee_groups = fee_filter_groups_payload(fees)
    levels = level_filter_payload(year)
    frais = request.GET.get("frais", "").strip().upper()
    periode = request.GET.get("periode", "").strip()
    selected_group = next((g for g in fee_groups if g["key"] == frais), None)
    current_filters = {
        "q": request.GET.get("q", ""),
        "option": request.GET.get("option", ""),
        "niveau": request.GET.get("niveau", ""),
        "frais": frais,
        "periode": periode,
    }
    return {
        "filter_options": active_options(),
        "filter_levels": levels,
        "filter_fee_groups": fee_groups,
        "selected_fee_group": selected_group,
        "current_filters": current_filters,
        "filters_active": any(current_filters.values()),
    }
