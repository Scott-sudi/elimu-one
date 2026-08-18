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
    from django.core.files.uploadedfile import UploadedFile

    student = Student.objects.select_for_update().get(pk=student.pk)
    photo_touched = False
    identity_fields = ("nom", "prenom", "postnom", "sexe", "date_naissance")
    identity_changed = any(
        field in data and data[field] != getattr(student, field)
        for field in identity_fields
    )
    if "photo" in data:
        photo = data["photo"]
        if photo is False:
            # Cleared via ClearableFileInput
            photo_touched = True
        elif isinstance(photo, UploadedFile):
            photo_touched = True
            validate_photo(photo)
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
    if photo_touched:
        from .card_service import refresh_cards_for_student

        refresh_cards_for_student(student, actor=actor, request=request)
    if identity_changed:
        student_id = student.pk

        def _push_student_update() -> None:
            from apps.api.parents_push import notify_guardians_of_student_updated
            from apps.secretariat.models import Student as S

            row = S.objects.filter(pk=student_id).first()
            if row is not None:
                notify_guardians_of_student_updated(student=row)

        transaction.on_commit(_push_student_update)
    return student


@transaction.atomic
def archive_student(student: Student, *, actor=None, request=None) -> Student:
    student = Student.objects.select_for_update().get(pk=student.pk)
    from apps.secretariat.models import StudentGuardian

    guardians = [
        link.guardian
        for link in StudentGuardian.objects.filter(
            student=student,
            guardian__is_archived=False,
            guardian__is_active=True,
        ).select_related("guardian")
    ]
    student.archive()
    audit_secretariat_action(
        action=AuditLog.Action.STUDENT_ARCHIVED,
        instance=student,
        description=f"Archivage de l'élève {student.matricule}",
        actor=actor,
        request=request,
    )
    if guardians:
        targets = list(guardians)
        student_id = student.pk

        def _push_archived() -> None:
            from apps.api.parents_push import notify_guardians_of_student_removed
            from apps.secretariat.models import Student as S

            row = S.objects.filter(pk=student_id).first()
            if row is not None:
                notify_guardians_of_student_removed(
                    student=row,
                    guardians=targets,
                    reason="Archivé",
                )

        transaction.on_commit(_push_archived)
    return student


@transaction.atomic
def delete_student_from_school(
    student: Student,
    *,
    reason: str,
    actor=None,
    request=None,
) -> Student:
    """
    Remove a pupil from school operations (class + parent app).

    - Cancels validated enrollments
    - Blocks student cards
    - Notifies linked guardians (push)
    - Unlinks guardians so the child disappears from the parent app
    - Archives the student (kept for audit; not hard-deleted)
    """
    from apps.secretariat.models import Enrollment, StudentCard, StudentGuardian

    motif = (reason or "").strip()
    if len(motif) < 5:
        raise SecretariatError("Indiquez un motif de suppression (au moins 5 caractères).")

    student = Student.objects.select_for_update().get(pk=student.pk)
    if student.is_archived:
        raise SecretariatError("Cet élève est déjà supprimé / archivé.")

    guardians = list(
        StudentGuardian.objects.filter(student=student)
        .select_related("guardian")
        .filter(guardian__is_archived=False, guardian__is_active=True)
    )
    guardian_objs = [link.guardian for link in guardians]

    display = " ".join(
        part for part in (student.nom, student.postnom, student.prenom) if part
    ) or student.matricule

    # Notify before unlinking so devices still resolve guardian↔student context.
    try:
        from apps.api.parents_push import notify_guardians_of_student_removed

        notify_guardians_of_student_removed(
            student=student,
            guardians=guardian_objs,
            reason=motif,
        )
    except Exception:
        # Push must not block school-side deletion.
        pass

    Enrollment.objects.filter(
        student=student,
        status=Enrollment.Status.VALIDATED,
    ).update(
        status=Enrollment.Status.CANCELLED,
        observation=f"Suppression école — {motif}",
    )

    for card in StudentCard.objects.filter(student=student, is_blocked=False):
        try:
            from .card_service import block_card

            block_card(
                card,
                reason=f"Élève supprimé de l'école — {motif}",
                actor=actor,
                request=request,
            )
        except SecretariatError:
            card.block(f"Élève supprimé — {motif}")

    StudentGuardian.objects.filter(student=student).delete()

    note = (student.observations or "").strip()
    tag = f"Supprimé de l'école — {motif}"
    student.observations = f"{note}\n{tag}".strip() if note else tag
    student.save(update_fields=["observations", "updated_at"])
    student.archive()

    audit_secretariat_action(
        action=AuditLog.Action.STUDENT_ARCHIVED,
        instance=student,
        description=f"Suppression de l'élève {student.matricule} ({display}) — motif : {motif}",
        actor=actor,
        request=request,
        new_values={"motif": motif, "matricule": student.matricule, "nom": display},
    )
    return student


@transaction.atomic
def restore_student(student: Student, *, actor=None, request=None) -> Student:
    student = Student.objects.select_for_update().get(pk=student.pk)
    if not student.is_archived:
        raise SecretariatError("Cet élève n'est pas archivé.")
    student.restore()
    audit_secretariat_action(
        action=AuditLog.Action.ENTITY_RESTORED,
        instance=student,
        description=f"Restauration de l'élève {student.matricule}",
        actor=actor,
        request=request,
    )
    return student
