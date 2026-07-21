"""Academic structure business operations."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.models import AuditLog
from apps.secretariat.models import AcademicYear, Option, SchoolClass, SchoolLevel, Section

from . import audit_secretariat_action
from .exceptions import SecretariatError


def _save(instance, *, actor=None, request=None, action=AuditLog.Action.ACADEMIC_CREATED):
    try:
        instance.full_clean()
        instance.save()
    except ValidationError as exc:
        raise SecretariatError("; ".join(exc.messages)) from exc
    audit_secretariat_action(
        action=action,
        instance=instance,
        description=f"{instance._meta.verbose_name.capitalize()} : {instance}",
        actor=actor,
        request=request,
    )
    return instance


@transaction.atomic
def create_academic_year(*, actor=None, request=None, **data) -> AcademicYear:
    if data.get("start_date") and data.get("end_date") and data["start_date"] >= data["end_date"]:
        raise SecretariatError("La date de fin doit être postérieure à la date de début.")
    year = AcademicYear(**data)
    if year.is_active:
        AcademicYear.objects.select_for_update().filter(is_active=True).update(is_active=False)
    return _save(year, actor=actor, request=request)


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
def close_academic_year(year: AcademicYear, *, actor=None, request=None) -> AcademicYear:
    year = AcademicYear.objects.select_for_update().get(pk=year.pk)
    year.is_closed = True
    year.is_active = False
    year.save(update_fields=["is_closed", "is_active", "updated_at"])
    audit_secretariat_action(
        action=AuditLog.Action.ACADEMIC_CLOSED,
        instance=year,
        description=f"Clôture de l'année scolaire {year.label}",
        actor=actor,
        request=request,
    )
    return year


def create_level(*, actor=None, request=None, **data) -> SchoolLevel:
    return _save(SchoolLevel(**data), actor=actor, request=request)


def create_section(*, actor=None, request=None, **data) -> Section:
    return _save(Section(**data), actor=actor, request=request)


def create_option(*, actor=None, request=None, **data) -> Option:
    section = data.get("section")
    if section and not section.is_active:
        raise SecretariatError("La section sélectionnée est inactive.")
    return _save(Option(**data), actor=actor, request=request)


def create_school_class(*, actor=None, request=None, **data) -> SchoolClass:
    year = data.get("academic_year")
    level = data.get("level")
    section = data.get("section")
    option = data.get("option")
    if not year or year.is_closed:
        raise SecretariatError("L'année scolaire est absente ou clôturée.")
    if not level or not level.is_active:
        raise SecretariatError("Le niveau sélectionné est absent ou inactif.")
    if section and not section.is_active:
        raise SecretariatError("La section sélectionnée est inactive.")
    if option and (not option.is_active or (option.section_id and option.section_id != getattr(section, "pk", None))):
        raise SecretariatError("L'option ne correspond pas à la section sélectionnée.")
    return _save(SchoolClass(**data), actor=actor, request=request)
