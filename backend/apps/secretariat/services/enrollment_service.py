"""Enrollment creation services."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.secretariat.models import Enrollment, SchoolClass, Student

from . import audit_secretariat_action
from .enrollment_number_service import generate_enrollment_number
from .exceptions import SecretariatError

ACTIVE_STATUSES = (Enrollment.Status.DRAFT, Enrollment.Status.VALIDATED)


@transaction.atomic
def create_enrollment(
    *,
    student: Student,
    school_class: SchoolClass,
    enrollment_type: str,
    enrollment_date=None,
    status: str = Enrollment.Status.VALIDATED,
    force_over_capacity: bool = False,
    actor=None,
    request=None,
    skip_reenrollment_guard: bool = False,
    **data,
) -> Enrollment:
    student = Student.objects.select_for_update().get(pk=student.pk)
    school_class = (
        SchoolClass.objects.select_for_update()
        .select_related("academic_year", "level")
        .get(pk=school_class.pk)
    )
    if student.is_archived or not student.is_active:
        raise SecretariatError("Cet élève est inactif ou archivé.")
    if not school_class.is_active or school_class.academic_year.is_closed:
        raise SecretariatError("La classe est inactive ou l'année scolaire est clôturée.")
    if Enrollment.objects.select_for_update().filter(
        student=student,
        academic_year=school_class.academic_year,
        status__in=ACTIVE_STATUSES,
    ).exists():
        raise SecretariatError("L'élève possède déjà une inscription active pour cette année.")

    # Continuity last year → must use réinscription, not a plain inscription.
    if (
        not skip_reenrollment_guard
        and enrollment_type == Enrollment.EnrollmentType.NEW
    ):
        from .reenrollment_service import find_reenrollment_source

        source = find_reenrollment_source(student, school_class)
        if source is not None:
            raise SecretariatError(
                "Cet élève a terminé l'année précédente dans le niveau immédiatement inférieur. "
                "Utilisez la réinscription pour cette classe."
            )

    current_count = Enrollment.objects.filter(
        school_class=school_class,
        status=Enrollment.Status.VALIDATED,
    ).count()
    if current_count >= school_class.max_capacity and not force_over_capacity:
        raise SecretariatError(
            "La classe a atteint sa capacité maximale. "
            "Élargissez le nombre de places (mot de passe + description) avant d'inscrire."
        )

    enrollment = Enrollment(
        student=student,
        academic_year=school_class.academic_year,
        school_class=school_class,
        enrollment_number=generate_enrollment_number(year=school_class.academic_year.start_date.year),
        enrollment_type=enrollment_type,
        enrollment_date=enrollment_date or timezone.localdate(),
        status=status,
        created_by=actor,
        **data,
    )
    try:
        enrollment.full_clean()
        enrollment.save()
    except ValidationError as exc:
        raise SecretariatError("; ".join(exc.messages)) from exc
    audit_secretariat_action(
        action=AuditLog.Action.ENROLLMENT_CREATED,
        instance=enrollment,
        description=f"Inscription {enrollment.enrollment_number} de {student.matricule}",
        actor=actor,
        request=request,
    )
    if status == Enrollment.Status.VALIDATED:
        from apps.finance.services.obligation_service import create_obligations_for_enrollment

        create_obligations_for_enrollment(enrollment=enrollment)
    return enrollment
