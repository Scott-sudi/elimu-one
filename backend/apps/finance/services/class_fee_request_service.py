"""Create class-scoped fee requests with once / tranche / month schedules."""

from __future__ import annotations

from calendar import monthrange
from datetime import date

from django.db import transaction

from apps.finance.models import FeeCategory, SchoolFee
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.fee_service import create_draft_fee, submit_fee
from apps.finance.services.fee_structure_service import (
    MONTH_LABELS_FR,
    iter_academic_months,
)
from apps.secretariat.models import AcademicYear, SchoolClass


def _tranche_label(base_label: str, index: int) -> str:
    if index == 1:
        suffix = "1ère tranche"
    else:
        suffix = f"{index}ème tranche"
    return f"{base_label} — {suffix}"


def _month_label(month_start: date) -> str:
    return f"{MONTH_LABELS_FR[month_start.month]} {month_start.year}"


def _last_day(month_start: date) -> date:
    return date(
        month_start.year,
        month_start.month,
        monthrange(month_start.year, month_start.month)[1],
    )


@transaction.atomic
def create_and_submit_class_fee_schedule(
    *,
    academic_year: AcademicYear,
    school_class: SchoolClass,
    code: str,
    label: str,
    amount,
    description: str,
    schedule_mode: str,
    tranche_count: int = 1,
    month_scope: str = "TOUS",
    month_keys: list[str] | None = None,
    actor=None,
    request=None,
) -> list[SchoolFee]:
    """
    Create one or more draft fees for a class and submit them to the secretariat.

    - UNE_FOIS → one column/tab fee
    - TRANCHES → N sibling fees (same group_key)
    - MOIS → one fee per selected academic month (or all months)
    """
    code = (code or "").strip().upper()
    label = (label or "").strip()
    if not code:
        raise FinanceError("Le code du frais est obligatoire.")
    if not label:
        raise FinanceError("Le nom du frais est obligatoire.")
    if SchoolFee.objects.filter(academic_year=academic_year, code__iexact=code).exists():
        raise FinanceError(
            f"Un frais avec le code « {code} » existe déjà pour cette année scolaire."
        )
    if SchoolFee.objects.filter(
        academic_year=academic_year, group_key__iexact=code
    ).exists():
        raise FinanceError(
            f"Un groupe de frais « {code} » existe déjà pour cette année scolaire."
        )

    category, _ = FeeCategory.objects.get_or_create(
        code="AUTRE",
        defaults={"name": "Autres frais", "order": 90, "is_active": True},
    )

    specs: list[dict] = []
    if schedule_mode == SchoolFee.ScheduleMode.TRANCHES:
        count = int(tranche_count or 0)
        if count < 2 or count > 12:
            raise FinanceError("Le nombre de tranches doit être entre 2 et 12.")
        for index in range(1, count + 1):
            specs.append(
                {
                    "code": f"{code}-T{index}"[:30],
                    "label": _tranche_label(label, index),
                    "period_index": index,
                    "due_date": None,
                }
            )
    elif schedule_mode == SchoolFee.ScheduleMode.MONTHS:
        months = iter_academic_months(academic_year)
        if month_scope == "SELECTION":
            wanted = set(month_keys or [])
            months = [m for m in months if f"{m.year}-{m.month:02d}" in wanted]
            if not months:
                raise FinanceError("Sélectionnez au moins un mois.")
        for index, month_start in enumerate(months, start=1):
            specs.append(
                {
                    "code": f"{code}-{month_start.year}{month_start.month:02d}"[:30],
                    "label": f"{label} — {_month_label(month_start)}",
                    "period_index": index,
                    "due_date": _last_day(month_start),
                }
            )
    else:
        schedule_mode = SchoolFee.ScheduleMode.ONCE
        specs.append(
            {
                "code": code[:30],
                "label": label,
                "period_index": 0,
                "due_date": None,
            }
        )

    created: list[SchoolFee] = []
    for spec in specs:
        fee = create_draft_fee(
            academic_year=academic_year,
            category=category,
            code=spec["code"],
            label=spec["label"],
            amount=amount,
            description=description,
            due_date=spec["due_date"],
            application_type=SchoolFee.ApplicationType.SELECTED_CLASSES,
            school_class_ids=[school_class.pk],
            schedule_mode=schedule_mode,
            group_key=code,
            period_index=spec["period_index"],
            actor=actor,
            request=request,
        )
        submit_fee(fee=fee, actor=actor, request=request)
        created.append(fee)
    return created
