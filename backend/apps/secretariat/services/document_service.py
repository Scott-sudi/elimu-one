"""Student document services."""

from __future__ import annotations

from pathlib import Path

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.secretariat.models import DocumentType, Enrollment, Student, StudentDocument

from . import audit_secretariat_action
from .exceptions import SecretariatError

MAX_DOCUMENT_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def _validate_file(file) -> None:
    if not file:
        raise SecretariatError("Le fichier du document est obligatoire.")
    if getattr(file, "size", 0) > MAX_DOCUMENT_SIZE:
        raise SecretariatError("Le document ne peut pas dépasser 10 Mo.")
    if Path(file.name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise SecretariatError("Le document doit être un PDF ou une image.")


@transaction.atomic
def upload_document(
    *,
    student: Student,
    document_type: DocumentType,
    file,
    received_at=None,
    actor=None,
    request=None,
    **data,
) -> StudentDocument:
    _validate_file(file)
    if student.is_archived:
        raise SecretariatError("Impossible d'ajouter un document à un élève archivé.")
    if not document_type.is_active:
        raise SecretariatError("Ce type de document est inactif.")
    document = StudentDocument.objects.create(
        student=student,
        document_type=document_type,
        file=file,
        received_at=received_at or timezone.now(),
        **data,
    )
    audit_secretariat_action(
        action=AuditLog.Action.DOCUMENT_UPLOADED,
        instance=document,
        description=f"Dépôt de {document_type.name} pour {student.matricule}",
        actor=actor,
        request=request,
    )
    return document


@transaction.atomic
def verify_document(
    document: StudentDocument,
    *,
    status: str,
    observation: str = "",
    actor=None,
    request=None,
) -> StudentDocument:
    document = StudentDocument.objects.select_for_update().get(pk=document.pk)
    if status not in StudentDocument.VerificationStatus.values:
        raise SecretariatError("Le statut de vérification est invalide.")
    if status == StudentDocument.VerificationStatus.REJECTED and not observation.strip():
        raise SecretariatError("Une observation est requise pour rejeter un document.")
    document.verification_status = status
    document.observation = observation
    document.verified_by = actor
    document.save(update_fields=["verification_status", "observation", "verified_by", "updated_at"])
    audit_secretariat_action(
        action=AuditLog.Action.DOCUMENT_VERIFIED,
        instance=document,
        description=f"Vérification du document de {document.student.matricule}",
        actor=actor,
        request=request,
    )
    return document


def document_completeness(student: Student, *, level=None) -> dict:
    if level is None:
        enrollment = (
            Enrollment.objects.filter(student=student, status=Enrollment.Status.VALIDATED)
            .select_related("school_class__level")
            .order_by("-academic_year__start_date")
            .first()
        )
        level = enrollment.school_class.level if enrollment else None
    required = DocumentType.objects.filter(is_active=True, is_required=True)
    if level:
        required = required.filter(Q(level__isnull=True) | Q(level=level))
    else:
        required = required.filter(level__isnull=True)
    received_ids = set(
        StudentDocument.objects.filter(
            student=student,
            verification_status=StudentDocument.VerificationStatus.VALIDATED,
            document_type__in=required,
        ).values_list("document_type_id", flat=True),
    )
    required_list = list(required)
    missing = [item for item in required_list if item.pk not in received_ids]
    total = len(required_list)
    return {
        "complete": not missing,
        "percentage": 100 if not total else round((total - len(missing)) * 100 / total),
        "required_count": total,
        "validated_count": total - len(missing),
        "missing": missing,
    }
