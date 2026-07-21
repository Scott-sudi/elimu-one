"""Single and bulk student reenrollment."""

from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction

from apps.audit.models import AuditLog
from apps.secretariat.models import Enrollment, SchoolClass

from . import audit_secretariat_action
from .enrollment_service import create_enrollment
from .exceptions import SecretariatError


@transaction.atomic
def reenroll_student(
    *,
    previous_enrollment: Enrollment,
    target_class: SchoolClass,
    force_over_capacity: bool = False,
    actor=None,
    request=None,
    **data,
) -> Enrollment:
    previous_enrollment = Enrollment.objects.select_for_update().select_related("student").get(
        pk=previous_enrollment.pk,
    )
    if previous_enrollment.status not in (Enrollment.Status.VALIDATED, Enrollment.Status.CLOSED):
        raise SecretariatError("Seule une inscription validée ou clôturée peut être réinscrite.")
    if target_class.academic_year_id == previous_enrollment.academic_year_id:
        raise SecretariatError("La réinscription doit concerner une nouvelle année scolaire.")
    enrollment = create_enrollment(
        student=previous_enrollment.student,
        school_class=target_class,
        enrollment_type=Enrollment.EnrollmentType.RENEWAL,
        force_over_capacity=force_over_capacity,
        actor=actor,
        request=request,
        **data,
    )
    audit_secretariat_action(
        action=AuditLog.Action.STUDENT_REENROLLED,
        instance=enrollment,
        description=f"Réinscription de {enrollment.student.matricule} en {target_class}",
        actor=actor,
        request=request,
    )
    return enrollment


@transaction.atomic
def bulk_reenroll(
    assignments: Iterable[tuple[Enrollment, SchoolClass]],
    *,
    force_over_capacity: bool = False,
    actor=None,
    request=None,
) -> list[Enrollment]:
    results = []
    for previous_enrollment, target_class in assignments:
        results.append(
            reenroll_student(
                previous_enrollment=previous_enrollment,
                target_class=target_class,
                force_over_capacity=force_over_capacity,
                actor=actor,
                request=request,
            ),
        )
    return results
