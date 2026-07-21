"""Communication drafting, targeting, and publication services."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.secretariat.models import (
    Communication,
    CommunicationReceipt,
    CommunicationTarget,
    Guardian,
    StudentGuardian,
)

from . import audit_secretariat_action
from .exceptions import SecretariatError

TARGET_FIELDS = {
    CommunicationTarget.TargetType.ACADEMIC_YEAR: "academic_year",
    CommunicationTarget.TargetType.LEVEL: "level",
    CommunicationTarget.TargetType.SECTION: "section",
    CommunicationTarget.TargetType.OPTION: "option",
    CommunicationTarget.TargetType.CLASS: "school_class",
    CommunicationTarget.TargetType.STUDENT: "student",
    CommunicationTarget.TargetType.GUARDIAN: "guardian",
}


def _validate_targets(targets: list[dict]) -> None:
    if not targets:
        raise SecretariatError("Au moins une cible de communication est requise.")
    for target in targets:
        target_type = target.get("target_type")
        if target_type not in CommunicationTarget.TargetType.values:
            raise SecretariatError("Un type de cible est invalide.")
        expected = TARGET_FIELDS.get(target_type)
        if expected and not target.get(expected):
            raise SecretariatError(f"La cible {target_type} est incomplète.")


def set_targets(communication: Communication, targets: list[dict]) -> None:
    _validate_targets(targets)
    if communication.targets.exists():
        raise SecretariatError("Les cibles existantes ne peuvent pas être supprimées directement.")
    CommunicationTarget.objects.bulk_create(
        [CommunicationTarget(communication=communication, **target) for target in targets],
    )


@transaction.atomic
def create_draft(*, targets: list[dict], actor=None, request=None, **data) -> Communication:
    data["status"] = Communication.Status.DRAFT
    data.setdefault("author", actor)
    communication = Communication.objects.create(**data)
    set_targets(communication, targets)
    audit_secretariat_action(
        action=AuditLog.Action.COMMUNICATION_DRAFTED,
        instance=communication,
        description=f"Création du brouillon « {communication.title} »",
        actor=actor,
        request=request,
    )
    return communication


def _recipient_links(communication: Communication):
    query = Q(pk__in=[])
    direct_guardians = set()
    for target in communication.targets.all():
        if target.target_type == CommunicationTarget.TargetType.ALL_PARENTS:
            query |= Q(student__enrollments__status="VALIDEE")
        elif target.target_type == CommunicationTarget.TargetType.ACADEMIC_YEAR:
            query |= Q(student__enrollments__academic_year=target.academic_year, student__enrollments__status="VALIDEE")
        elif target.target_type == CommunicationTarget.TargetType.LEVEL:
            query |= Q(student__enrollments__school_class__level=target.level, student__enrollments__status="VALIDEE")
        elif target.target_type == CommunicationTarget.TargetType.SECTION:
            query |= Q(student__enrollments__school_class__section=target.section, student__enrollments__status="VALIDEE")
        elif target.target_type == CommunicationTarget.TargetType.OPTION:
            query |= Q(student__enrollments__school_class__option=target.option, student__enrollments__status="VALIDEE")
        elif target.target_type == CommunicationTarget.TargetType.CLASS:
            query |= Q(student__enrollments__school_class=target.school_class, student__enrollments__status="VALIDEE")
        elif target.target_type == CommunicationTarget.TargetType.STUDENT:
            query |= Q(student=target.student)
        elif target.target_type == CommunicationTarget.TargetType.GUARDIAN:
            direct_guardians.add(target.guardian_id)
    links = StudentGuardian.objects.filter(query, receives_notifications=True).select_related("guardian", "student").distinct()
    return links, direct_guardians


def _create_receipts(communication: Communication) -> None:
    links, direct_guardians = _recipient_links(communication)
    rows = [
        CommunicationReceipt(communication=communication, guardian=link.guardian, student=link.student)
        for link in links
    ]
    rows.extend(
        CommunicationReceipt(communication=communication, guardian=guardian)
        for guardian in Guardian.objects.filter(pk__in=direct_guardians, is_active=True)
    )
    CommunicationReceipt.objects.bulk_create(rows, ignore_conflicts=True)


@transaction.atomic
def publish(communication: Communication, *, actor=None, request=None) -> Communication:
    communication = Communication.objects.select_for_update().get(pk=communication.pk)
    if communication.status not in (Communication.Status.DRAFT, Communication.Status.SCHEDULED):
        raise SecretariatError("Seul un brouillon ou une communication programmée peut être publié.")
    if not communication.targets.exists():
        raise SecretariatError("La communication ne possède aucune cible.")
    communication.status = Communication.Status.PUBLISHED
    communication.published_at = timezone.now()
    communication.save(update_fields=["status", "published_at", "updated_at"])
    _create_receipts(communication)
    audit_secretariat_action(
        action=AuditLog.Action.COMMUNICATION_PUBLISHED,
        instance=communication,
        description=f"Publication de « {communication.title} »",
        actor=actor,
        request=request,
    )
    return communication


@transaction.atomic
def schedule(communication: Communication, *, publish_at, actor=None, request=None) -> Communication:
    communication = Communication.objects.select_for_update().get(pk=communication.pk)
    if communication.status != Communication.Status.DRAFT:
        raise SecretariatError("Seul un brouillon peut être programmé.")
    if publish_at <= timezone.now():
        raise SecretariatError("La date de publication doit être dans le futur.")
    communication.status = Communication.Status.SCHEDULED
    communication.published_at = publish_at
    communication.save(update_fields=["status", "published_at", "updated_at"])
    audit_secretariat_action(
        action=AuditLog.Action.COMMUNICATION_SCHEDULED,
        instance=communication,
        description=f"Programmation de « {communication.title} »",
        actor=actor,
        request=request,
    )
    return communication


@transaction.atomic
def archive(communication: Communication, *, actor=None, request=None) -> Communication:
    communication = Communication.objects.select_for_update().get(pk=communication.pk)
    communication.status = Communication.Status.ARCHIVED
    communication.is_pinned = False
    communication.save(update_fields=["status", "is_pinned", "updated_at"])
    audit_secretariat_action(
        action=AuditLog.Action.COMMUNICATION_ARCHIVED,
        instance=communication,
        description=f"Archivage de « {communication.title} »",
        actor=actor,
        request=request,
    )
    return communication
