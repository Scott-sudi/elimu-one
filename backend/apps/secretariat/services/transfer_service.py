"""Same-year class transfer services."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.secretariat.models import ClassTransfer, Enrollment, SchoolClass

from . import audit_secretariat_action
from .exceptions import SecretariatError


@transaction.atomic
def transfer_student(
    *,
    enrollment: Enrollment,
    to_class: SchoolClass,
    motif: str,
    transfer_date=None,
    force_over_capacity: bool = False,
    actor=None,
    request=None,
) -> ClassTransfer:
    enrollment = Enrollment.objects.select_for_update().select_related("student", "school_class").get(pk=enrollment.pk)
    to_class = SchoolClass.objects.select_for_update().get(pk=to_class.pk)
    if enrollment.status != Enrollment.Status.VALIDATED:
        raise SecretariatError("Seule une inscription validée peut être transférée.")
    if enrollment.academic_year_id != to_class.academic_year_id:
        raise SecretariatError("Le transfert doit rester dans la même année scolaire.")
    if enrollment.school_class_id == to_class.pk:
        raise SecretariatError("La classe de destination doit être différente.")
    if not to_class.is_active:
        raise SecretariatError("La classe de destination est inactive.")
    occupied = Enrollment.objects.filter(
        school_class=to_class,
        status=Enrollment.Status.VALIDATED,
    ).count()
    if occupied >= to_class.max_capacity and not force_over_capacity:
        raise SecretariatError("La classe de destination a atteint sa capacité maximale.")
    if not motif.strip():
        raise SecretariatError("Le motif du transfert est obligatoire.")

    from_class = enrollment.school_class
    enrollment.school_class = to_class
    enrollment.save(update_fields=["school_class", "updated_at"])
    transfer = ClassTransfer.objects.create(
        student=enrollment.student,
        enrollment=enrollment,
        from_class=from_class,
        to_class=to_class,
        motif=motif.strip(),
        transfer_date=transfer_date or timezone.localdate(),
        performed_by=actor,
    )
    audit_secretariat_action(
        action=AuditLog.Action.CLASS_TRANSFERRED,
        instance=transfer,
        description=f"Transfert de {enrollment.student.matricule} de {from_class} vers {to_class}",
        actor=actor,
        request=request,
    )
    return transfer
