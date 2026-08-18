"""Academic structure business operations."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.models import AuditLog
from apps.secretariat.models import (
    AcademicYear,
    Enrollment,
    Option,
    SchoolClass,
    SchoolLevel,
    Section,
)

from . import audit_secretariat_action
from .exceptions import SecretariatError


def _validation_error_message(exc: ValidationError) -> str:
    """Flatten Django validation errors into a single French-facing alert."""
    if hasattr(exc, "message_dict"):
        parts: list[str] = []
        for messages in exc.message_dict.values():
            parts.extend(messages)
        if parts:
            return " ".join(parts)
    return "; ".join(exc.messages)


def _save(instance, *, actor=None, request=None, action=AuditLog.Action.ACADEMIC_CREATED):
    try:
        instance.full_clean()
        instance.save()
    except ValidationError as exc:
        raise SecretariatError(_validation_error_message(exc)) from exc
    audit_secretariat_action(
        action=action,
        instance=instance,
        description=f"{instance._meta.verbose_name.capitalize()} : {instance}",
        actor=actor,
        request=request,
    )
    return instance


def _set_active(instance, *, is_active: bool, actor=None, request=None):
    instance = instance.__class__.objects.select_for_update().get(pk=instance.pk)
    instance.is_active = is_active
    instance.save(update_fields=["is_active", "updated_at"])
    audit_secretariat_action(
        action=AuditLog.Action.ENTITY_REACTIVATED if is_active else AuditLog.Action.ENTITY_DEACTIVATED,
        instance=instance,
        description=(
            f"{'Réactivation' if is_active else 'Désactivation'} de "
            f"{instance._meta.verbose_name} « {instance} »"
        ),
        actor=actor,
        request=request,
    )
    return instance


@transaction.atomic
def create_academic_year(*, actor=None, request=None, **data) -> AcademicYear:
    if data.get("start_date") and data.get("end_date") and data["start_date"] >= data["end_date"]:
        raise SecretariatError("La date de fin doit être postérieure à la date de début.")
    assert_can_create_academic_year()
    year = AcademicYear(**data)
    if year.is_active:
        AcademicYear.objects.select_for_update().filter(is_active=True).update(is_active=False)
    return _save(year, actor=actor, request=request)


def get_open_current_year() -> AcademicYear | None:
    """Return the année scolaire en cours (active and not closed), if any."""
    return AcademicYear.objects.filter(is_active=True, is_closed=False).first()


def can_create_academic_year() -> bool:
    return get_open_current_year() is None


def assert_can_create_academic_year() -> None:
    current = get_open_current_year()
    if current is not None:
        raise SecretariatError(
            "Désolé, vous ne pouvez pas créer une nouvelle année scolaire "
            f"tant que l'année en cours ({current.label}) n'est pas clôturée."
        )


@transaction.atomic
def update_academic_year(year: AcademicYear, *, actor=None, request=None, **data) -> AcademicYear:
    year = AcademicYear.objects.select_for_update().get(pk=year.pk)
    for field, value in data.items():
        setattr(year, field, value)
    if year.start_date >= year.end_date:
        raise SecretariatError("La date de fin doit être postérieure à la date de début.")
    return _save(
        year,
        actor=actor,
        request=request,
        action=AuditLog.Action.ACADEMIC_UPDATED,
    )


@transaction.atomic
def delete_academic_year(year: AcademicYear, *, actor=None, request=None) -> None:
    year = AcademicYear.objects.select_for_update().get(pk=year.pk)
    if year.is_active:
        raise SecretariatError(
            "Impossible de supprimer l'année scolaire active. "
            "Activez une autre année ou désactivez celle-ci d'abord."
        )
    if year.school_classes.exists():
        raise SecretariatError(
            "Impossible de supprimer cette année scolaire : des classes y sont liées. "
            "Supprimez ou réaffectez les classes d'abord."
        )
    if year.enrollments.exists():
        raise SecretariatError(
            "Impossible de supprimer cette année scolaire : des inscriptions y sont liées."
        )
    label = year.label
    public_id = str(year.public_id)
    entity_type = year._meta.label
    year.delete()
    from apps.audit.services import log_action

    log_action(
        request=request,
        actor=actor,
        action=AuditLog.Action.ENTITY_DELETED,
        description=f"Suppression de l'année scolaire {label}",
        entity_type=entity_type,
        entity_public_id=public_id,
        old_values={"label": label, "public_id": public_id},
    )


@transaction.atomic
def activate_academic_year(year: AcademicYear, *, actor=None, request=None) -> AcademicYear:
    year = AcademicYear.objects.select_for_update().get(pk=year.pk)
    if year.is_closed:
        raise SecretariatError("Une année scolaire clôturée ne peut pas être activée.")
    AcademicYear.objects.select_for_update().exclude(pk=year.pk).filter(is_active=True).update(is_active=False)
    year.is_active = True
    year.save(update_fields=["is_active", "updated_at"])
    audit_secretariat_action(
        action=AuditLog.Action.ACADEMIC_ACTIVATED,
        instance=year,
        description=f"Activation de l'année scolaire {year.label}",
        actor=actor,
        request=request,
    )
    return year


@transaction.atomic
def close_academic_year(
    year: AcademicYear,
    *,
    closure_notes: str = "",
    actor=None,
    request=None,
) -> AcademicYear:
    year = AcademicYear.objects.select_for_update().get(pk=year.pk)
    if year.is_closed:
        raise SecretariatError("Cette année scolaire est déjà clôturée.")
    year.is_closed = True
    year.is_active = False
    year.closure_notes = (closure_notes or "").strip()
    year.save(update_fields=["is_closed", "is_active", "closure_notes", "updated_at"])

    from apps.secretariat.services.card_service import block_cards_for_academic_year

    blocked_count = block_cards_for_academic_year(year, actor=actor, request=request)

    new_values = {"blocked_cards": blocked_count}
    if year.closure_notes:
        new_values["closure_notes"] = year.closure_notes
    audit_secretariat_action(
        action=AuditLog.Action.ACADEMIC_CLOSED,
        instance=year,
        description=(
            f"Clôture de l'année scolaire {year.label}"
            + (f" — {year.closure_notes[:120]}" if year.closure_notes else "")
            + (f" · {blocked_count} carte(s) bloquée(s)" if blocked_count else "")
        ),
        actor=actor,
        request=request,
        new_values=new_values,
    )
    return year


def create_level(*, actor=None, request=None, **data) -> SchoolLevel:
    return _save(SchoolLevel(**data), actor=actor, request=request)


@transaction.atomic
def update_level(level: SchoolLevel, *, actor=None, request=None, **data) -> SchoolLevel:
    level = SchoolLevel.objects.select_for_update().get(pk=level.pk)
    for field, value in data.items():
        setattr(level, field, value)
    return _save(level, actor=actor, request=request, action=AuditLog.Action.ACADEMIC_UPDATED)


@transaction.atomic
def deactivate_level(level: SchoolLevel, *, actor=None, request=None) -> SchoolLevel:
    return _set_active(level, is_active=False, actor=actor, request=request)


@transaction.atomic
def reactivate_level(level: SchoolLevel, *, actor=None, request=None) -> SchoolLevel:
    return _set_active(level, is_active=True, actor=actor, request=request)


@transaction.atomic
def delete_level(level: SchoolLevel, *, actor=None, request=None) -> None:
    level = SchoolLevel.objects.select_for_update().get(pk=level.pk)
    if level.school_classes.exists():
        raise SecretariatError(
            "Impossible de supprimer ce niveau : des classes l'utilisent. "
            "Désactivez-le plutôt pour le retirer de la sélection."
        )
    name = str(level)
    public_id = str(level.public_id)
    level.delete()
    audit_secretariat_action(
        action=AuditLog.Action.ENTITY_DELETED,
        instance=level,
        description=f"Suppression du niveau « {name} »",
        actor=actor,
        request=request,
        old_values={"name": name, "public_id": public_id},
    )


def create_section(*, actor=None, request=None, **data) -> Section:
    return _save(Section(**data), actor=actor, request=request)


@transaction.atomic
def update_section(section: Section, *, actor=None, request=None, **data) -> Section:
    section = Section.objects.select_for_update().get(pk=section.pk)
    for field, value in data.items():
        setattr(section, field, value)
    return _save(section, actor=actor, request=request, action=AuditLog.Action.ACADEMIC_UPDATED)


@transaction.atomic
def deactivate_section(section: Section, *, actor=None, request=None) -> Section:
    return _set_active(section, is_active=False, actor=actor, request=request)


@transaction.atomic
def reactivate_section(section: Section, *, actor=None, request=None) -> Section:
    return _set_active(section, is_active=True, actor=actor, request=request)


@transaction.atomic
def delete_section(section: Section, *, actor=None, request=None) -> None:
    section = Section.objects.select_for_update().get(pk=section.pk)
    if section.options.exists() or section.school_classes.exists():
        raise SecretariatError(
            "Impossible de supprimer cette section : des options ou des classes y sont liées. "
            "Désactivez-la plutôt pour la retirer de la sélection."
        )
    name = str(section)
    public_id = str(section.public_id)
    section.delete()
    audit_secretariat_action(
        action=AuditLog.Action.ENTITY_DELETED,
        instance=section,
        description=f"Suppression de la section « {name} »",
        actor=actor,
        request=request,
        old_values={"name": name, "public_id": public_id},
    )


def create_option(*, actor=None, request=None, **data) -> Option:
    section = data.get("section")
    if section and not section.is_active:
        raise SecretariatError("La section sélectionnée est inactive.")
    return _save(Option(**data), actor=actor, request=request)


@transaction.atomic
def update_option(option: Option, *, actor=None, request=None, **data) -> Option:
    option = Option.objects.select_for_update().get(pk=option.pk)
    for field, value in data.items():
        setattr(option, field, value)
    section = option.section
    if section and not section.is_active:
        raise SecretariatError("La section sélectionnée est inactive.")
    return _save(option, actor=actor, request=request, action=AuditLog.Action.ACADEMIC_UPDATED)


@transaction.atomic
def deactivate_option(option: Option, *, actor=None, request=None) -> Option:
    return _set_active(option, is_active=False, actor=actor, request=request)


@transaction.atomic
def reactivate_option(option: Option, *, actor=None, request=None) -> Option:
    return _set_active(option, is_active=True, actor=actor, request=request)


@transaction.atomic
def delete_option(option: Option, *, actor=None, request=None) -> None:
    option = Option.objects.select_for_update().get(pk=option.pk)
    if option.school_classes.exists():
        raise SecretariatError(
            "Impossible de supprimer cette option : des classes l'utilisent. "
            "Désactivez-la plutôt pour la retirer de la sélection."
        )
    name = str(option)
    public_id = str(option.public_id)
    option.delete()
    audit_secretariat_action(
        action=AuditLog.Action.ENTITY_DELETED,
        instance=option,
        description=f"Suppression de l'option « {name} »",
        actor=actor,
        request=request,
        old_values={"name": name, "public_id": public_id},
    )


def create_school_class(*, actor=None, request=None, **data) -> SchoolClass:
    year = data.get("academic_year")
    level = data.get("level")
    section = data.get("section")
    option = data.get("option")
    letter = (data.get("letter") or "").strip().upper()
    if letter:
        data["letter"] = letter
    if not year or year.is_closed:
        raise SecretariatError("L'année scolaire est absente ou clôturée.")
    if not level or not level.is_active:
        raise SecretariatError("Le niveau sélectionné est absent ou inactif.")
    if section and not section.is_active:
        raise SecretariatError("La section sélectionnée est inactive.")
    if option and (not option.is_active or (option.section_id and option.section_id != getattr(section, "pk", None))):
        raise SecretariatError("L'option ne correspond pas à la section sélectionnée.")
    if not letter:
        raise SecretariatError("Veuillez choisir la lettre de la classe (A, B, C, D…).")
    allowed_letters = {choice for choice, _ in SchoolClass.LETTER_CHOICES}
    if letter not in allowed_letters:
        raise SecretariatError("Lettre de classe invalide.")
    return _save(SchoolClass(**data), actor=actor, request=request)


@transaction.atomic
def update_school_class(school_class: SchoolClass, *, actor=None, request=None, **data) -> SchoolClass:
    school_class = SchoolClass.objects.select_for_update().select_related("academic_year").get(pk=school_class.pk)
    if school_class.academic_year.is_closed:
        raise SecretariatError(
            "Cette année scolaire est clôturée. Consultation uniquement — "
            "aucune modification n'est possible."
        )
    if not school_class.is_active:
        raise SecretariatError(
            "Cette classe est désactivée. Consultation uniquement — aucune modification n'est possible."
        )
    allowed = {"name", "max_capacity", "room", "description", "code", "is_active"}
    for field, value in data.items():
        if field in allowed:
            setattr(school_class, field, value)
    return _save(
        school_class,
        actor=actor,
        request=request,
        action=AuditLog.Action.ACADEMIC_UPDATED,
    )


@transaction.atomic
def expand_class_capacity(
    school_class: SchoolClass,
    *,
    new_capacity,
    reason: str = "",
    actor=None,
    request=None,
) -> SchoolClass:
    """Increase max capacity for a full class (audited; password checked in the view)."""
    school_class = (
        SchoolClass.objects.select_for_update()
        .select_related("academic_year")
        .get(pk=school_class.pk)
    )
    if school_class.academic_year.is_closed:
        raise SecretariatError(
            "Cette année scolaire est clôturée. Consultation uniquement — "
            "aucune modification n'est possible."
        )
    if not school_class.is_active:
        raise SecretariatError(
            "Cette classe est désactivée. Consultation uniquement — aucune modification n'est possible."
        )
    reason = (reason or "").strip()
    if not reason:
        raise SecretariatError("Indiquez une description pour l'élargissement des places.")
    try:
        new_capacity = int(new_capacity)
    except (TypeError, ValueError) as exc:
        raise SecretariatError("Capacité invalide.") from exc
    if new_capacity <= school_class.max_capacity:
        raise SecretariatError(
            f"La nouvelle capacité doit être supérieure à {school_class.max_capacity}."
        )
    old_capacity = school_class.max_capacity
    school_class.max_capacity = new_capacity
    try:
        school_class.full_clean()
        school_class.save(update_fields=["max_capacity", "updated_at"])
    except ValidationError as exc:
        raise SecretariatError("; ".join(exc.messages)) from exc
    audit_secretariat_action(
        action=AuditLog.Action.ACADEMIC_UPDATED,
        instance=school_class,
        description=(
            f"Élargissement capacité « {school_class.name} » : "
            f"{old_capacity} → {new_capacity} — {reason[:160]}"
        ),
        actor=actor,
        request=request,
        old_values={"max_capacity": old_capacity, "reason": reason},
        new_values={"max_capacity": new_capacity},
    )
    return school_class


@transaction.atomic
def deactivate_school_class(school_class: SchoolClass, *, actor=None, request=None) -> SchoolClass:
    school_class = SchoolClass.objects.select_for_update().select_related("academic_year").get(pk=school_class.pk)
    if school_class.academic_year.is_closed:
        raise SecretariatError(
            "Cette année scolaire est clôturée. Consultation uniquement — "
            "aucune modification n'est possible."
        )
    return _set_active(school_class, is_active=False, actor=actor, request=request)


@transaction.atomic
def reactivate_school_class(school_class: SchoolClass, *, actor=None, request=None) -> SchoolClass:
    raise SecretariatError("La réactivation d'une classe n'est plus autorisée.")


@transaction.atomic
def delete_school_class(
    school_class: SchoolClass,
    *,
    deletion_reason: str = "",
    actor=None,
    request=None,
) -> None:
    school_class = SchoolClass.objects.select_for_update().select_related("academic_year").get(pk=school_class.pk)
    if school_class.academic_year.is_closed:
        raise SecretariatError(
            "Cette année scolaire est clôturée. Consultation uniquement — "
            "aucune modification n'est possible."
        )
    if not school_class.is_active:
        raise SecretariatError(
            "Cette classe est désactivée. Consultation uniquement — aucune modification n'est possible."
        )
    if Enrollment.objects.filter(school_class=school_class).exists():
        raise SecretariatError(
            "Impossible de supprimer cette classe : des inscriptions y sont liées. "
            "Désactivez-la plutôt."
        )
    if school_class.outgoing_transfers.exists() or school_class.incoming_transfers.exists():
        raise SecretariatError(
            "Impossible de supprimer cette classe : des transferts y sont liés. "
            "Désactivez-la plutôt."
        )
    reason = (deletion_reason or "").strip()
    if not reason:
        raise SecretariatError("Indiquez la raison de la suppression.")
    name = str(school_class)
    public_id = str(school_class.public_id)
    audit_secretariat_action(
        action=AuditLog.Action.ENTITY_DELETED,
        instance=school_class,
        description=f"Suppression de la classe « {name} » — {reason[:160]}",
        actor=actor,
        request=request,
        old_values={"name": name, "public_id": public_id, "reason": reason},
    )
    school_class.delete()
