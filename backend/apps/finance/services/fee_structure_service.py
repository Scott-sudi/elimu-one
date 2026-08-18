"""Structural fee boards: Minerval (months), Frais de l'État (3 tranches), Autres."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.finance.models import FeeApprovalHistory, FeeCategory, SchoolFee
from apps.finance.services.fee_service import ensure_default_fee_categories
from apps.finance.services.obligation_service import create_obligations_for_fee
from apps.secretariat.models import AcademicYear

BOARD_MINERVAL = "minerval"
BOARD_ETAT = "etat"

# Plus d'onglets structurels : les frais (minerval, État, etc.) se créent
# uniquement via « Créer frais ». Conservé pour seeds / démo uniquement.
BOARD_CHOICES = ()

CATEGORY_CODES_BY_BOARD = {
    BOARD_MINERVAL: ("MINERVAL", "SCOLARITE"),
    BOARD_ETAT: ("FRAIS_ETAT",),
}

CUSTOM_FEE_CATEGORY_CODES = ("AUTRE", "INSCRIPTION", "EXAMEN", "TENUE")

DEFAULT_MINERVAL_AMOUNT = Decimal("50000.00")
DEFAULT_ETAT_AMOUNT = Decimal("25000.00")

MONTH_LABELS_FR = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}

ETAT_TRANCHES = (
    ("ETAT-T1", "1ère tranche", 1),
    ("ETAT-T2", "2ème tranche", 2),
    ("ETAT-T3", "3ème tranche", 3),
)

STRUCTURE_CATEGORIES = (
    {"code": "MINERVAL", "name": "Minerval", "order": 5},
    {"code": "FRAIS_ETAT", "name": "Frais de l'État", "order": 15},
    {"code": "SCOLARITE", "name": "Scolarité", "order": 10},
    {"code": "INSCRIPTION", "name": "Inscription", "order": 20},
    {"code": "EXAMEN", "name": "Examens", "order": 30},
    {"code": "TENUE", "name": "Tenue / uniforme", "order": 40},
    {"code": "AUTRE", "name": "Autres frais", "order": 90},
)


def ensure_board_categories() -> dict[str, FeeCategory]:
    """Ensure board categories exist and return them by code."""
    ensure_default_fee_categories()
    for item in STRUCTURE_CATEGORIES:
        FeeCategory.objects.get_or_create(
            code=item["code"],
            defaults={
                "name": item["name"],
                "order": item["order"],
                "is_active": True,
                "description": "",
            },
        )
    return {
        c.code: c
        for c in FeeCategory.objects.filter(
            code__in=[item["code"] for item in STRUCTURE_CATEGORIES]
        )
    }


def iter_academic_months(academic_year: AcademicYear) -> list[date]:
    """Return first-of-month dates from year start through year end (inclusive)."""
    start = academic_year.start_date.replace(day=1)
    end = academic_year.end_date.replace(day=1)
    months: list[date] = []
    current = start
    while current <= end:
        months.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
        if len(months) > 18:
            break
    return months


def month_column_label(month_start: date) -> str:
    return f"{MONTH_LABELS_FR[month_start.month]} {month_start.year}"


def minerval_fee_code(month_start: date) -> str:
    return f"MIN-{month_start.year}{month_start.month:02d}"


def _last_day(month_start: date) -> date:
    return date(
        month_start.year,
        month_start.month,
        monthrange(month_start.year, month_start.month)[1],
    )


@transaction.atomic
def ensure_structural_fees(
    *,
    academic_year: AcademicYear,
    actor=None,
    minerval_amount: Decimal = DEFAULT_MINERVAL_AMOUNT,
    etat_amount: Decimal = DEFAULT_ETAT_AMOUNT,
) -> dict[str, list[SchoolFee]]:
    """
    Demo/seed helper only — creates Minerval months + État tranches already approved.

    Production UI must NOT call this: the accountant creates fees manually, then
    secretariat approves them. Prefer an empty fee list with « Créer un frais ».
    """
    categories = ensure_board_categories()
    minerval_cat = categories["MINERVAL"]
    etat_cat = categories["FRAIS_ETAT"]
    created_or_existing: dict[str, list[SchoolFee]] = {
        BOARD_MINERVAL: [],
        BOARD_ETAT: [],
    }

    for month_start in iter_academic_months(academic_year):
        code = minerval_fee_code(month_start)
        label = month_column_label(month_start)
        fee, created = SchoolFee.objects.get_or_create(
            academic_year=academic_year,
            code=code,
            defaults={
                "category": minerval_cat,
                "label": label,
                "description": "Minerval mensuel (structure comptable).",
                "amount": minerval_amount,
                "currency": "CDF",
                "due_date": _last_day(month_start),
                "is_mandatory": True,
                "allow_partial": True,
                "application_type": SchoolFee.ApplicationType.ALL_CLASSES,
                "status": SchoolFee.Status.APPROVED,
                "created_by": actor,
                "reviewed_by": actor,
                "reviewed_at": timezone.now() if actor else None,
                "is_active": True,
                "is_archived": False,
            },
        )
        if created:
            FeeApprovalHistory.objects.create(
                fee=fee,
                action=FeeApprovalHistory.Action.APPROVED,
                previous_status="",
                new_status=SchoolFee.Status.APPROVED,
                comment="Structure minerval créée automatiquement.",
                actor=actor,
            )
            create_obligations_for_fee(fee=fee)
        else:
            create_obligations_for_fee(fee=fee)
        created_or_existing[BOARD_MINERVAL].append(fee)

    for code, label, order in ETAT_TRANCHES:
        fee, created = SchoolFee.objects.get_or_create(
            academic_year=academic_year,
            code=code,
            defaults={
                "category": etat_cat,
                "label": label,
                "description": f"Frais de l'État — {label}.",
                "amount": etat_amount,
                "currency": "CDF",
                "due_date": None,
                "is_mandatory": True,
                "allow_partial": True,
                "application_type": SchoolFee.ApplicationType.ALL_CLASSES,
                "status": SchoolFee.Status.APPROVED,
                "created_by": actor,
                "reviewed_by": actor,
                "reviewed_at": timezone.now() if actor else None,
                "is_active": True,
                "is_archived": False,
            },
        )
        if created:
            FeeApprovalHistory.objects.create(
                fee=fee,
                action=FeeApprovalHistory.Action.APPROVED,
                previous_status="",
                new_status=SchoolFee.Status.APPROVED,
                comment="Structure frais de l'État créée automatiquement.",
                actor=actor,
            )
        create_obligations_for_fee(fee=fee)
        created_or_existing[BOARD_ETAT].append(fee)

    # Stable order
    created_or_existing[BOARD_MINERVAL].sort(
        key=lambda f: (f.due_date or date.min, f.code)
    )
    created_or_existing[BOARD_ETAT].sort(key=lambda f: f.code)
    return created_or_existing


@transaction.atomic
def archive_auto_structural_fees_without_payments(*, academic_year: AcademicYear) -> int:
    """
    Archive auto-created Minerval / État fees that have no payment allocation.

    Used once when switching production to manual fee creation.
    Fees with at least one payment are left untouched.
    """
    from apps.finance.models import PaymentAllocation

    qs = SchoolFee.objects.filter(
        academic_year=academic_year,
        is_archived=False,
    ).filter(
        Q(code__startswith="MIN-")
        | Q(code__in=["ETAT-T1", "ETAT-T2", "ETAT-T3"])
        | Q(description__icontains="structure comptable")
        | Q(description__icontains="Frais de l'État —")
    )
    archived = 0
    for fee in qs:
        has_payment = PaymentAllocation.objects.filter(obligation__fee=fee).exists()
        if has_payment:
            continue
        fee.is_archived = True
        fee.is_active = False
        fee.save(update_fields=["is_archived", "is_active", "updated_at"])
        archived += 1
    return archived


def fees_for_board(
    *,
    academic_year: AcademicYear,
    board: str,
) -> list[SchoolFee]:
    """Approved active fees belonging to a board for the academic year."""
    codes = CATEGORY_CODES_BY_BOARD.get(board, ())
    qs = (
        SchoolFee.objects.filter(
            academic_year=academic_year,
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
            category__code__in=codes,
        )
        .select_related("category")
    )
    if board == BOARD_MINERVAL:
        return list(qs.order_by("due_date", "code", "label"))
    if board == BOARD_ETAT:
        return list(qs.order_by("code", "label"))
    return list(qs.order_by("category__order", "label", "code"))


def custom_fees_for_class(*, school_class) -> list[SchoolFee]:
    """
    Approved custom fees that apply to this class (flat list).
    Prefer custom_fee_groups_for_class() for tab rendering.
    """
    from apps.finance.services.fee_service import fee_applies_to_class

    fees = list(
        SchoolFee.objects.filter(
            academic_year_id=school_class.academic_year_id,
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
            category__code__in=CUSTOM_FEE_CATEGORY_CODES,
        )
        .select_related("category")
        .prefetch_related("targets")
        .order_by("group_key", "period_index", "label", "code")
    )
    return [fee for fee in fees if fee_applies_to_class(fee, school_class)]


def custom_fee_groups_for_class(*, school_class) -> list[dict]:
    """
    Group approved custom fees by group_key for class board tabs.

    Each group → one tab; fees inside → matrix columns.
    """
    fees = custom_fees_for_class(school_class=school_class)
    groups: dict[str, dict] = {}
    for fee in fees:
        key = (fee.group_key or fee.code).strip().upper()
        if key not in groups:
            # Tab title: strip " — …" suffix from first fee label when grouped
            base_label = fee.label.split(" — ")[0].strip() if " — " in fee.label else fee.label
            groups[key] = {
                "key": key,
                "label": base_label,
                "fees": [],
                "schedule_mode": fee.schedule_mode,
            }
        groups[key]["fees"].append(fee)
    return list(groups.values())


def payable_fees_for_class(*, school_class) -> list[SchoolFee]:
    """Approved fees that apply to this class (for payment combobox)."""
    from apps.finance.services.fee_service import fee_applies_to_class

    fees = list(
        SchoolFee.objects.filter(
            academic_year_id=school_class.academic_year_id,
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
        )
        .select_related("category")
        .prefetch_related("targets")
        .order_by("category__order", "group_key", "period_index", "label", "code")
    )
    return [fee for fee in fees if fee_applies_to_class(fee, school_class)]


def payable_fees_for_year(*, academic_year) -> list[SchoolFee]:
    """All approved active fees of the year (fallback when no class context)."""
    return list(
        SchoolFee.objects.filter(
            academic_year=academic_year,
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
        )
        .select_related("category")
        .order_by("category__order", "group_key", "period_index", "label", "code")
    )
