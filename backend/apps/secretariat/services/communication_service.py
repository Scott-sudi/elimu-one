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

EDITABLE_STATUSES = (
    Communication.Status.DRAFT,
    Communication.Status.SCHEDULED,
    Communication.Status.PUBLISHED,
)


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


def set_targets(
    communication: Communication,
    targets: list[dict],
    *,
    replace: bool = False,
) -> None:
    _validate_targets(targets)
    if communication.targets.exists():
        if not replace:
            raise SecretariatError("Les cibles existantes ne peuvent pas être remplacées directement.")
        communication.targets.all().delete()
    CommunicationTarget.objects.bulk_create(
        [CommunicationTarget(communication=communication, **target) for target in targets],
    )


@transaction.atomic
def create_draft(*, targets: list[dict], actor=None, request=None, **data) -> Communication:
    data["status"] = Communication.Status.DRAFT
    data.setdefault("author", actor)
    data.pop("is_pinned", None)
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


@transaction.atomic
def update_communication(
    communication: Communication,
    *,
    targets: list[dict] | None = None,
    actor=None,
    request=None,
    **data,
) -> Communication:
    communication = Communication.objects.select_for_update().get(pk=communication.pk)
    if communication.status == Communication.Status.ARCHIVED:
        raise SecretariatError("Une communication archivée ne peut pas être modifiée. Restaurez-la d'abord.")

    desired_status = data.pop("status", None)
    data.pop("is_pinned", None)
    data.pop("author", None)

    for field, value in data.items():
        setattr(communication, field, value)
    communication.save()

    if targets is not None:
        set_targets(communication, targets, replace=True)
        if communication.status == Communication.Status.PUBLISHED:
            CommunicationReceipt.objects.filter(communication=communication).delete()
            _create_receipts(communication)

    if desired_status and desired_status != communication.status:
        if desired_status == Communication.Status.PUBLISHED:
            return publish(communication, actor=actor, request=request)
        if desired_status == Communication.Status.DRAFT:
            return unpublish(communication, actor=actor, request=request)
        raise SecretariatError("Statut de communication non autorisé pour cette action.")

    audit_secretariat_action(
        action=AuditLog.Action.COMMUNICATION_DRAFTED,
        instance=communication,
        description=f"Modification de « {communication.title} »",
        actor=actor,
        request=request,
    )
    if communication.status == Communication.Status.PUBLISHED:
        try:
            from apps.api.parents_push import notify_guardians_of_communication

            comm_id = communication.pk

            def _push_updated() -> None:
                from apps.secretariat.models import Communication as C

                comm = C.objects.filter(pk=comm_id).first()
                if comm is not None:
                    notify_guardians_of_communication(
                        communication=comm, updated=True
                    )

            transaction.on_commit(_push_updated)
        except Exception:
            pass
    return communication


@transaction.atomic
def delete_communication(communication: Communication, *, actor=None, request=None) -> None:
    communication = Communication.objects.select_for_update().get(pk=communication.pk)
    title = communication.title
    audit_secretariat_action(
        action=AuditLog.Action.ENTITY_DELETED,
        instance=communication,
        description=f"Suppression de la communication « {title} »",
        actor=actor,
        request=request,
        old_values={"title": title, "status": communication.status},
    )
    communication.delete()



def _recipient_links(communication: Communication):
    query = Q(pk__in=[])
    direct_guardians = set()
    for target in communication.targets.all():
        if target.target_type == CommunicationTarget.TargetType.ALL_PARENTS:
            query |= Q(student__enrollments__status="VALIDEE")
        elif target.target_type == CommunicationTarget.TargetType.ACADEMIC_YEAR:
            query |= Q(
                student__enrollments__academic_year=target.academic_year,
                student__enrollments__status="VALIDEE",
            )
        elif target.target_type == CommunicationTarget.TargetType.LEVEL:
            query |= Q(
                student__enrollments__school_class__level=target.level,
                student__enrollments__status="VALIDEE",
            )
        elif target.target_type == CommunicationTarget.TargetType.SECTION:
            query |= Q(
                student__enrollments__school_class__section=target.section,
                student__enrollments__status="VALIDEE",
            )
        elif target.target_type == CommunicationTarget.TargetType.OPTION:
            query |= Q(
                student__enrollments__school_class__option=target.option,
                student__enrollments__status="VALIDEE",
            )
        elif target.target_type == CommunicationTarget.TargetType.CLASS:
            query |= Q(
                student__enrollments__school_class=target.school_class,
                student__enrollments__status="VALIDEE",
            )
        elif target.target_type == CommunicationTarget.TargetType.STUDENT:
            query |= Q(student=target.student)
        elif target.target_type == CommunicationTarget.TargetType.GUARDIAN:
            direct_guardians.add(target.guardian_id)
    links = (
        StudentGuardian.objects.filter(query, receives_notifications=True)
        .select_related("guardian", "student")
        .distinct()
    )
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
def publish(
    communication: Communication,
    *,
    targets: list[dict] | None = None,
    actor=None,
    request=None,
) -> Communication:
    communication = Communication.objects.select_for_update().get(pk=communication.pk)
    if communication.status not in (Communication.Status.DRAFT, Communication.Status.SCHEDULED):
        raise SecretariatError("Seul un brouillon ou une communication programmée peut être publié.")
    if targets is not None:
        set_targets(communication, targets, replace=True)
    if not communication.targets.exists():
        raise SecretariatError(
            "Choisissez les destinataires : tous les parents, une classe, ou un élève."
        )
    communication.status = Communication.Status.PUBLISHED
    communication.published_at = timezone.now()
    communication.save(update_fields=["status", "published_at", "updated_at"])
    CommunicationReceipt.objects.filter(communication=communication).delete()
    _create_receipts(communication)
    audit_secretariat_action(
        action=AuditLog.Action.COMMUNICATION_PUBLISHED,
        instance=communication,
        description=f"Publication de « {communication.title} »",
        actor=actor,
        request=request,
    )
    try:
        from apps.api.parents_push import notify_guardians_of_communication

        notify_guardians_of_communication(communication=communication)
    except Exception:
        # Ne jamais bloquer la publication si le push échoue.
        pass
    return communication


@transaction.atomic
def unpublish(communication: Communication, *, actor=None, request=None) -> Communication:
    communication = Communication.objects.select_for_update().get(pk=communication.pk)
    if communication.status != Communication.Status.PUBLISHED:
        raise SecretariatError("Seule une communication publiée peut repasser en brouillon.")
    communication.status = Communication.Status.DRAFT
    communication.published_at = None
    communication.save(update_fields=["status", "published_at", "updated_at"])
    CommunicationReceipt.objects.filter(communication=communication).delete()
    audit_secretariat_action(
        action=AuditLog.Action.COMMUNICATION_DRAFTED,
        instance=communication,
        description=f"Retour en brouillon de « {communication.title} »",
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
def pin(communication: Communication, *, actor=None, request=None) -> Communication:
    communication = Communication.objects.select_for_update().get(pk=communication.pk)
    if communication.status == Communication.Status.ARCHIVED:
        raise SecretariatError("Une communication archivée ne peut pas être épinglée.")
    communication.is_pinned = True
    communication.pinned_at = timezone.now()
    communication.pinned_by = actor
    communication.save(update_fields=["is_pinned", "pinned_at", "pinned_by", "updated_at"])
    audit_secretariat_action(
        action=AuditLog.Action.COMMUNICATION_PINNED,
        instance=communication,
        description=f"Épinglage de « {communication.title} »",
        actor=actor,
        request=request,
    )
    return communication


@transaction.atomic
def unpin(communication: Communication, *, actor=None, request=None) -> Communication:
    communication = Communication.objects.select_for_update().get(pk=communication.pk)
    communication.is_pinned = False
    communication.pinned_at = None
    communication.pinned_by = None
    communication.save(update_fields=["is_pinned", "pinned_at", "pinned_by", "updated_at"])
    audit_secretariat_action(
        action=AuditLog.Action.COMMUNICATION_UNPINNED,
        instance=communication,
        description=f"Désépinglage de « {communication.title} »",
        actor=actor,
        request=request,
    )
    return communication


@transaction.atomic
def archive(communication: Communication, *, actor=None, request=None) -> Communication:
    communication = Communication.objects.select_for_update().get(pk=communication.pk)
    communication.status = Communication.Status.ARCHIVED
    communication.is_pinned = False
    communication.pinned_at = None
    communication.pinned_by = None
    communication.save(
        update_fields=["status", "is_pinned", "pinned_at", "pinned_by", "updated_at"]
    )
    audit_secretariat_action(
        action=AuditLog.Action.COMMUNICATION_ARCHIVED,
        instance=communication,
        description=f"Archivage de « {communication.title} »",
        actor=actor,
        request=request,
    )
    return communication


@transaction.atomic
def restore(communication: Communication, *, actor=None, request=None) -> Communication:
    """Restore an archived communication to draft status."""
    communication = Communication.objects.select_for_update().get(pk=communication.pk)
    if communication.status != Communication.Status.ARCHIVED:
        raise SecretariatError("Seule une communication archivée peut être restaurée.")
    communication.status = Communication.Status.DRAFT
    communication.save(update_fields=["status", "updated_at"])
    audit_secretariat_action(
        action=AuditLog.Action.ENTITY_RESTORED,
        instance=communication,
        description=f"Restauration de « {communication.title} » en brouillon",
        actor=actor,
        request=request,
    )
    return communication
