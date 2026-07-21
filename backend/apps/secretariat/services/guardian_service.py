"""Guardian management and student association services."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet

from apps.audit.models import AuditLog
from apps.secretariat.models import Guardian, Student, StudentGuardian

from . import audit_secretariat_action
from .exceptions import SecretariatError


def _save_guardian(guardian: Guardian) -> Guardian:
    try:
        guardian.full_clean()
        guardian.save()
    except ValidationError as exc:
        raise SecretariatError("; ".join(exc.messages)) from exc
    return guardian


def create_guardian(*, actor=None, request=None, **data) -> Guardian:
    guardian = _save_guardian(Guardian(**data))
    audit_secretariat_action(
        action=AuditLog.Action.GUARDIAN_CREATED,
        instance=guardian,
        description=f"Création du responsable {guardian}",
        actor=actor,
        request=request,
    )
    return guardian


@transaction.atomic
def update_guardian(guardian: Guardian, *, actor=None, request=None, **data) -> Guardian:
    guardian = Guardian.objects.select_for_update().get(pk=guardian.pk)
    for field, value in data.items():
        if field not in {"id", "pk", "public_id"}:
            setattr(guardian, field, value)
    _save_guardian(guardian)
    audit_secretariat_action(
        action=AuditLog.Action.GUARDIAN_UPDATED,
        instance=guardian,
        description=f"Modification du responsable {guardian}",
        actor=actor,
        request=request,
    )
    return guardian


def find_guardian_candidates(
    *,
    phone: str = "",
    email: str = "",
    name: str = "",
) -> QuerySet[Guardian]:
    query = Q()
    if phone:
        query |= Q(telephone_principal__icontains=phone) | Q(telephone_secondaire__icontains=phone)
    if email:
        query |= Q(email__iexact=email)
    if name:
        for term in name.split():
            query &= Q(nom__icontains=term) | Q(postnom__icontains=term) | Q(prenom__icontains=term)
    return Guardian.objects.filter(query, is_archived=False).distinct() if query else Guardian.objects.none()


@transaction.atomic
def associate_guardian(
    *,
    student: Student,
    guardian: Guardian,
    lien_parente: str,
    is_primary: bool = False,
    actor=None,
    request=None,
    **data,
) -> StudentGuardian:
    student = Student.objects.select_for_update().get(pk=student.pk)
    if student.is_archived or guardian.is_archived:
        raise SecretariatError("Un élève ou responsable archivé ne peut pas être associé.")
    links = StudentGuardian.objects.select_for_update().filter(student=student)
    is_primary = is_primary or not links.exists()
    if is_primary:
        links.filter(is_primary=True).update(is_primary=False)
    link, _ = StudentGuardian.objects.update_or_create(
        student=student,
        guardian=guardian,
        defaults={"lien_parente": lien_parente, "is_primary": is_primary, **data},
    )
    audit_secretariat_action(
        action=AuditLog.Action.GUARDIAN_ASSOCIATED,
        instance=student,
        description=f"Association de {guardian} à l'élève {student.matricule}",
        actor=actor,
        request=request,
    )
    return link
