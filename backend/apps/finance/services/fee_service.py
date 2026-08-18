"""School fee draft lifecycle services (create, update, submit, withdraw, archive)."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.finance.models import FeeApprovalHistory, FeeCategory, FeeTarget, SchoolFee
from apps.finance.services import audit_finance_action
from apps.finance.services.exceptions import FinanceError
from apps.secretariat.models import (
    AcademicYear,
    Option,
    SchoolClass,
    SchoolLevel,
    Section,
)

DEFAULT_FEE_CATEGORIES = (
    {"code": "MINERVAL", "name": "Minerval", "order": 5},
    {"code": "FRAIS_ETAT", "name": "Frais de l'État", "order": 15},
    {"code": "SCOLARITE", "name": "Scolarité", "order": 10},
    {"code": "INSCRIPTION", "name": "Inscription", "order": 20},
    {"code": "EXAMEN", "name": "Examens", "order": 30},
    {"code": "TENUE", "name": "Tenue / uniforme", "order": 40},
    {"code": "AUTRE", "name": "Autres frais", "order": 90},
)


def ensure_default_fee_categories() -> list[FeeCategory]:
    """Create the default fee categories if they are missing."""
    for item in DEFAULT_FEE_CATEGORIES:
        FeeCategory.objects.get_or_create(
            code=item["code"],
            defaults={
                "name": item["name"],
                "order": item["order"],
                "is_active": True,
                "description": "",
            },
        )
    return list(FeeCategory.objects.filter(is_active=True).order_by("order", "name"))


def resolve_target_classes(fee: SchoolFee) -> QuerySet[SchoolClass]:
    """Return active classes of the fee's year that match its application targets."""
    qs = SchoolClass.objects.filter(
        academic_year_id=fee.academic_year_id,
        is_active=True,
    )
    app_type = fee.application_type

    if app_type == SchoolFee.ApplicationType.ALL_CLASSES:
        return qs

    targets = fee.targets.all()
    if app_type == SchoolFee.ApplicationType.SELECTED_CLASSES:
        class_ids = [
            t.school_class_id for t in targets if t.school_class_id is not None
        ]
        return qs.filter(pk__in=class_ids)

    if app_type == SchoolFee.ApplicationType.LEVEL:
        level_ids = [t.level_id for t in targets if t.level_id is not None]
        return qs.filter(level_id__in=level_ids)

    if app_type == SchoolFee.ApplicationType.SECTION:
        section_ids = [t.section_id for t in targets if t.section_id is not None]
        return qs.filter(section_id__in=section_ids)

    if app_type == SchoolFee.ApplicationType.OPTION:
        option_ids = [t.option_id for t in targets if t.option_id is not None]
        return qs.filter(option_id__in=option_ids)

    return qs.none()


def fee_applies_to_class(fee: SchoolFee, school_class: SchoolClass) -> bool:
    """Whether the fee's targeting includes the given class."""
    if fee.academic_year_id != school_class.academic_year_id:
        return False
    return resolve_target_classes(fee).filter(pk=school_class.pk).exists()


def _fee_snapshot(fee: SchoolFee) -> dict:
    return {
        "public_id": str(fee.public_id),
        "code": fee.code,
        "label": fee.label,
        "amount": str(fee.amount),
        "currency": fee.currency,
        "status": fee.status,
        "application_type": fee.application_type,
        "is_mandatory": fee.is_mandatory,
        "allow_partial": fee.allow_partial,
        "is_active": fee.is_active,
        "is_archived": fee.is_archived,
    }


def _record_history(
    *,
    fee: SchoolFee,
    action: str,
    previous_status: str,
    new_status: str,
    actor=None,
    comment: str = "",
) -> FeeApprovalHistory:
    return FeeApprovalHistory.objects.create(
        fee=fee,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        comment=comment,
        actor=actor,
    )


def _validate_amount(amount) -> Decimal:
    try:
        value = Decimal(str(amount))
    except Exception as exc:
        raise FinanceError("Montant invalide.") from exc
    if value <= 0:
        raise FinanceError("Le montant doit être supérieur à zéro.")
    return value.quantize(Decimal("0.01"))


def _validate_application_targets(
    *,
    application_type: str,
    academic_year: AcademicYear,
    school_class_ids: Iterable[int] | None = None,
    level_ids: Iterable[int] | None = None,
    section_ids: Iterable[int] | None = None,
    option_ids: Iterable[int] | None = None,
) -> list[dict]:
    """Build validated target payloads for FeeTarget creation."""
    school_class_ids = list(school_class_ids or [])
    level_ids = list(level_ids or [])
    section_ids = list(section_ids or [])
    option_ids = list(option_ids or [])

    if application_type == SchoolFee.ApplicationType.ALL_CLASSES:
        return []

    if application_type == SchoolFee.ApplicationType.SELECTED_CLASSES:
        if not school_class_ids:
            raise FinanceError("Sélectionnez au moins une classe.")
        classes = list(
            SchoolClass.objects.filter(
                pk__in=school_class_ids,
                academic_year=academic_year,
            )
        )
        if len(classes) != len(set(school_class_ids)):
            raise FinanceError(
                "Une ou plusieurs classes sélectionnées sont invalides pour cette année."
            )
        return [{"school_class": c} for c in classes]

    if application_type == SchoolFee.ApplicationType.LEVEL:
        if not level_ids:
            raise FinanceError("Sélectionnez au moins un niveau.")
        levels = list(SchoolLevel.objects.filter(pk__in=level_ids, is_active=True))
        if len(levels) != len(set(level_ids)):
            raise FinanceError("Un ou plusieurs niveaux sélectionnés sont invalides.")
        return [{"level": level} for level in levels]

    if application_type == SchoolFee.ApplicationType.SECTION:
        if not section_ids:
            raise FinanceError("Sélectionnez au moins une section.")
        sections = list(Section.objects.filter(pk__in=section_ids, is_active=True))
        if len(sections) != len(set(section_ids)):
            raise FinanceError("Une ou plusieurs sections sélectionnées sont invalides.")
        return [{"section": section} for section in sections]

    if application_type == SchoolFee.ApplicationType.OPTION:
        if not option_ids:
            raise FinanceError("Sélectionnez au moins une option.")
        options = list(Option.objects.filter(pk__in=option_ids, is_active=True))
        if len(options) != len(set(option_ids)):
            raise FinanceError("Une ou plusieurs options sélectionnées sont invalides.")
        return [{"option": option} for option in options]

    raise FinanceError("Type d'application invalide.")


def _replace_targets(fee: SchoolFee, target_payloads: list[dict]) -> None:
    fee.targets.all().delete()
    FeeTarget.objects.bulk_create(
        [FeeTarget(fee=fee, **payload) for payload in target_payloads]
    )


@transaction.atomic
def create_draft_fee(
    *,
    academic_year: AcademicYear,
    category: FeeCategory,
    code: str,
    label: str,
    amount,
    currency: str = "CDF",
    description: str = "",
    due_date=None,
    is_mandatory: bool = True,
    allow_partial: bool = True,
    application_type: str = SchoolFee.ApplicationType.ALL_CLASSES,
    school_class_ids: Iterable[int] | None = None,
    level_ids: Iterable[int] | None = None,
    section_ids: Iterable[int] | None = None,
    option_ids: Iterable[int] | None = None,
    schedule_mode: str = SchoolFee.ScheduleMode.ONCE,
    group_key: str = "",
    period_index: int = 0,
    actor=None,
    request=None,
) -> SchoolFee:
    """Create a school fee in draft status with optional targets."""
    if academic_year.is_closed:
        raise FinanceError("Impossible de créer un frais sur une année clôturée.")
    if not category.is_active:
        raise FinanceError("La catégorie de frais est inactive.")

    code = (code or "").strip().upper()
    label = (label or "").strip()
    group_key = (group_key or code).strip().upper()
    if not code:
        raise FinanceError("Le code du frais est obligatoire.")
    if not label:
        raise FinanceError("Le libellé du frais est obligatoire.")
    if SchoolFee.objects.filter(academic_year=academic_year, code__iexact=code).exists():
        raise FinanceError(
            f"Un frais avec le code « {code} » existe déjà pour cette année scolaire."
        )

    amount_value = _validate_amount(amount)
    currency = (currency or "CDF").strip().upper() or "CDF"
    if application_type not in SchoolFee.ApplicationType.values:
        raise FinanceError("Type d'application invalide.")
    if schedule_mode not in SchoolFee.ScheduleMode.values:
        schedule_mode = SchoolFee.ScheduleMode.ONCE

    target_payloads = _validate_application_targets(
        application_type=application_type,
        academic_year=academic_year,
        school_class_ids=school_class_ids,
        level_ids=level_ids,
        section_ids=section_ids,
        option_ids=option_ids,
    )

    fee = SchoolFee.objects.create(
        academic_year=academic_year,
        category=category,
        code=code,
        label=label,
        description=(description or "").strip(),
        amount=amount_value,
        currency=currency,
        due_date=due_date,
        is_mandatory=bool(is_mandatory),
        allow_partial=bool(allow_partial),
        application_type=application_type,
        schedule_mode=schedule_mode,
        group_key=group_key,
        period_index=int(period_index or 0),
        status=SchoolFee.Status.DRAFT,
        created_by=actor,
        is_active=True,
        is_archived=False,
    )
    _replace_targets(fee, target_payloads)
    _record_history(
        fee=fee,
        action=FeeApprovalHistory.Action.CREATED,
        previous_status="",
        new_status=SchoolFee.Status.DRAFT,
        actor=actor,
    )
    audit_finance_action(
        action=AuditLog.Action.FEE_CREATED,
        instance=fee,
        description=f"Création du frais {fee.code} ({fee.label})",
        actor=actor,
        request=request,
        new_values=_fee_snapshot(fee),
    )
    return fee


@transaction.atomic
def update_draft_fee(
    *,
    fee: SchoolFee,
    category: FeeCategory | None = None,
    code: str | None = None,
    label: str | None = None,
    amount=None,
    currency: str | None = None,
    description: str | None = None,
    due_date=None,
    clear_due_date: bool = False,
    is_mandatory: bool | None = None,
    allow_partial: bool | None = None,
    application_type: str | None = None,
    school_class_ids: Iterable[int] | None = None,
    level_ids: Iterable[int] | None = None,
    section_ids: Iterable[int] | None = None,
    option_ids: Iterable[int] | None = None,
    update_targets: bool = False,
    actor=None,
    request=None,
) -> SchoolFee:
    """Update a draft or rejected fee (editable before resubmission)."""
    fee = SchoolFee.objects.select_for_update().get(pk=fee.pk)
    if fee.status not in {SchoolFee.Status.DRAFT, SchoolFee.Status.REJECTED}:
        raise FinanceError(
            "Seuls les frais en brouillon ou rejetés peuvent être modifiés."
        )
    if fee.is_archived:
        raise FinanceError("Ce frais est archivé et ne peut plus être modifié.")

    old_values = _fee_snapshot(fee)
    previous_status = fee.status

    if category is not None:
        if not category.is_active:
            raise FinanceError("La catégorie de frais est inactive.")
        fee.category = category
    if code is not None:
        code = code.strip().upper()
        if not code:
            raise FinanceError("Le code du frais est obligatoire.")
        conflict = SchoolFee.objects.filter(
            academic_year_id=fee.academic_year_id,
            code__iexact=code,
        ).exclude(pk=fee.pk)
        if conflict.exists():
            raise FinanceError(
                f"Un frais avec le code « {code} » existe déjà pour cette année scolaire."
            )
        fee.code = code
    if label is not None:
        label = label.strip()
        if not label:
            raise FinanceError("Le libellé du frais est obligatoire.")
        fee.label = label
    if amount is not None:
        fee.amount = _validate_amount(amount)
    if currency is not None:
        fee.currency = currency.strip().upper() or "CDF"
    if description is not None:
        fee.description = description.strip()
    if clear_due_date:
        fee.due_date = None
    elif due_date is not None:
        fee.due_date = due_date
    if is_mandatory is not None:
        fee.is_mandatory = bool(is_mandatory)
    if allow_partial is not None:
        fee.allow_partial = bool(allow_partial)

    if application_type is not None:
        if application_type not in SchoolFee.ApplicationType.values:
            raise FinanceError("Type d'application invalide.")
        fee.application_type = application_type
        update_targets = True

    if update_targets:
        target_payloads = _validate_application_targets(
            application_type=fee.application_type,
            academic_year=fee.academic_year,
            school_class_ids=school_class_ids,
            level_ids=level_ids,
            section_ids=section_ids,
            option_ids=option_ids,
        )
        _replace_targets(fee, target_payloads)

    # Rejected fees return to draft after edit.
    if fee.status == SchoolFee.Status.REJECTED:
        fee.status = SchoolFee.Status.DRAFT
        fee.rejection_reason = ""
        fee.reviewed_by = None
        fee.reviewed_at = None

    fee.save()
    _record_history(
        fee=fee,
        action=FeeApprovalHistory.Action.UPDATED,
        previous_status=previous_status,
        new_status=fee.status,
        actor=actor,
    )
    audit_finance_action(
        action=AuditLog.Action.FEE_UPDATED,
        instance=fee,
        description=f"Modification du frais {fee.code}",
        actor=actor,
        request=request,
        old_values=old_values,
        new_values=_fee_snapshot(fee),
    )
    return fee


@transaction.atomic
def submit_fee(*, fee: SchoolFee, actor=None, request=None) -> SchoolFee:
    """Submit a draft fee for secretary approval."""
    fee = SchoolFee.objects.select_for_update().get(pk=fee.pk)
    if fee.status not in {SchoolFee.Status.DRAFT, SchoolFee.Status.REJECTED}:
        raise FinanceError("Seuls les frais en brouillon ou rejetés peuvent être soumis.")
    if fee.is_archived or not fee.is_active:
        raise FinanceError("Ce frais ne peut pas être soumis.")
    if fee.application_type != SchoolFee.ApplicationType.ALL_CLASSES:
        if not fee.targets.exists():
            raise FinanceError(
                "Définissez les cibles d'application avant de soumettre ce frais."
            )
        if not resolve_target_classes(fee).exists():
            raise FinanceError(
                "Aucune classe active ne correspond aux cibles de ce frais."
            )

    previous_status = fee.status
    fee.status = SchoolFee.Status.PENDING
    fee.submitted_at = timezone.now()
    fee.rejection_reason = ""
    fee.reviewed_by = None
    fee.reviewed_at = None
    fee.save(
        update_fields=[
            "status",
            "submitted_at",
            "rejection_reason",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )
    _record_history(
        fee=fee,
        action=FeeApprovalHistory.Action.SUBMITTED,
        previous_status=previous_status,
        new_status=fee.status,
        actor=actor,
    )
    audit_finance_action(
        action=AuditLog.Action.FEE_SUBMITTED,
        instance=fee,
        description=f"Soumission du frais {fee.code} pour validation",
        actor=actor,
        request=request,
        new_values=_fee_snapshot(fee),
    )
    return fee


@transaction.atomic
def withdraw_fee(*, fee: SchoolFee, actor=None, request=None) -> SchoolFee:
    """Withdraw a pending fee back to draft."""
    fee = SchoolFee.objects.select_for_update().get(pk=fee.pk)
    if fee.status != SchoolFee.Status.PENDING:
        raise FinanceError("Seuls les frais en attente peuvent être retirés.")

    previous_status = fee.status
    fee.status = SchoolFee.Status.DRAFT
    fee.submitted_at = None
    fee.save(update_fields=["status", "submitted_at", "updated_at"])
    _record_history(
        fee=fee,
        action=FeeApprovalHistory.Action.WITHDRAWN,
        previous_status=previous_status,
        new_status=fee.status,
        actor=actor,
    )
    audit_finance_action(
        action=AuditLog.Action.FEE_WITHDRAWN,
        instance=fee,
        description=f"Retrait de la demande du frais {fee.code}",
        actor=actor,
        request=request,
        new_values=_fee_snapshot(fee),
    )
    return fee


@transaction.atomic
def archive_fee(*, fee: SchoolFee, actor=None, request=None) -> SchoolFee:
    """Archive a fee (soft deactivate). Approved fees keep existing obligations."""
    fee = SchoolFee.objects.select_for_update().get(pk=fee.pk)
    if fee.is_archived:
        raise FinanceError("Ce frais est déjà archivé.")
    if fee.status == SchoolFee.Status.PENDING:
        raise FinanceError(
            "Retirez d'abord la demande en attente avant d'archiver ce frais."
        )

    previous_status = fee.status
    old_values = _fee_snapshot(fee)
    fee.is_archived = True
    fee.is_active = False
    fee.status = SchoolFee.Status.ARCHIVED
    fee.save(update_fields=["is_archived", "is_active", "status", "updated_at"])
    _record_history(
        fee=fee,
        action=FeeApprovalHistory.Action.ARCHIVED,
        previous_status=previous_status,
        new_status=fee.status,
        actor=actor,
    )
    audit_finance_action(
        action=AuditLog.Action.FEE_ARCHIVED,
        instance=fee,
        description=f"Archivage du frais {fee.code}",
        actor=actor,
        request=request,
        old_values=old_values,
        new_values=_fee_snapshot(fee),
    )
    return fee
