"""Student lifecycle services."""

from __future__ import annotations

from PIL import Image, UnidentifiedImageError
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.secretariat.models import Student

from . import audit_secretariat_action
from .exceptions import SecretariatError
from .matricule_service import generate_matricule

MAX_PHOTO_SIZE = 5 * 1024 * 1024
ALLOWED_PHOTO_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_photo(photo) -> None:
    if not photo:
        return
    if getattr(photo, "size", 0) > MAX_PHOTO_SIZE:
        raise SecretariatError("La photo ne peut pas dépasser 5 Mo.")
    try:
        image = Image.open(photo)
        if image.format not in ALLOWED_PHOTO_FORMATS:
            raise SecretariatError("La photo doit être au format JPEG, PNG ou WEBP.")
        image.verify()
        photo.seek(0)
    except (UnidentifiedImageError, OSError) as exc:
        raise SecretariatError("Le fichier fourni n'est pas une image valide.") from exc


def _validate_student(student: Student) -> None:
    if student.date_naissance > timezone.localdate():
        raise SecretariatError("La date de naissance ne peut pas être dans le futur.")
    try:
        student.full_clean()
    except ValidationError as exc:
        raise SecretariatError("; ".join(exc.messages)) from exc


@transaction.atomic
def create_student(*, actor=None, request=None, **data) -> Student:
    validate_photo(data.get("photo"))
    data.setdefault("matricule", generate_matricule())
    student = Student(**data)
    _validate_student(student)
    student.save()
    audit_secretariat_action(
        action=AuditLog.Action.STUDENT_CREATED,
        instance=student,
        description=f"Création de l'élève {student.matricule}",
        actor=actor,
        request=request,
    )
    return student


@transaction.atomic
def update_student(student: Student, *, actor=None, request=None, **data) -> Student:
    student = Student.objects.select_for_update().get(pk=student.pk)
    if "photo" in data:
        validate_photo(data["photo"])
    for field, value in data.items():
        if field not in {"id", "pk", "public_id", "matricule"}:
            setattr(student, field, value)
    _validate_student(student)
    student.save()
    audit_secretariat_action(
        action=AuditLog.Action.STUDENT_UPDATED,
        instance=student,
        description=f"Modification de l'élève {student.matricule}",
        actor=actor,
        request=request,
    )
    return student


@transaction.atomic
def archive_student(student: Student, *, actor=None, request=None) -> Student:
    student = Student.objects.select_for_update().get(pk=student.pk)
    student.archive()
    audit_secretariat_action(
        action=AuditLog.Action.STUDENT_ARCHIVED,
        instance=student,
        description=f"Archivage de l'élève {student.matricule}",
        actor=actor,
        request=request,
    )
    return student
