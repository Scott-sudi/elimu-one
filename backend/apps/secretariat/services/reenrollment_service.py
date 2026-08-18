"""Single and bulk student reenrollment with progression rules."""

from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction
from django.db.models import QuerySet

from apps.audit.models import AuditLog
from apps.secretariat.models import AcademicYear, Enrollment, SchoolClass

from . import audit_secretariat_action
from .enrollment_service import ACTIVE_STATUSES, create_enrollment
from .exceptions import SecretariatError

PREVIOUS_ELIGIBLE_STATUSES = (Enrollment.Status.VALIDATED, Enrollment.Status.CLOSED)


def get_previous_closed_year(academic_year: AcademicYear) -> AcademicYear | None:
    """Most recent closed year before the given academic year."""
    return (
        AcademicYear.objects.filter(
            is_closed=True,
            start_date__lt=academic_year.start_date,
        )
        .order_by("-start_date")
        .first()
    )


def source_level_order_for(target_class: SchoolClass) -> int | None:
    """Level order that must have been completed last year to reenroll here."""
    order = getattr(target_class.level, "order", None)
    if order is None or order <= 0:
        return None
    return order - 1


def find_reenrollment_source(
    student,
    target_class: SchoolClass,
) -> Enrollment | None:
    """
    Return the previous-year enrollment that makes this student eligible
    for réinscription into target_class, or None.
    """
    previous_year = get_previous_closed_year(target_class.academic_year)
    if previous_year is None:
        return None
    source_order = source_level_order_for(target_class)
    if source_order is None:
        return None
    return (
        Enrollment.objects.filter(
            student=student,
            academic_year=previous_year,
            status__in=PREVIOUS_ELIGIBLE_STATUSES,
            school_class__level__order=source_order,
        )
        .select_related("student", "school_class", "school_class__level", "academic_year")
        .order_by("-enrollment_date", "-id")
        .first()
    )


def eligible_reenrollments_for_class(target_class: SchoolClass) -> QuerySet[Enrollment]:
    """Candidates from the previous closed year, immediately lower level, not yet enrolled this year."""
    previous_year = get_previous_closed_year(target_class.academic_year)
    source_order = source_level_order_for(target_class)
    if previous_year is None or source_order is None:
        return Enrollment.objects.none()

    already_enrolled = Enrollment.objects.filter(
        academic_year=target_class.academic_year,
        status__in=ACTIVE_STATUSES,
    ).values_list("student_id", flat=True)

    return (
        Enrollment.objects.filter(
            academic_year=previous_year,
            status__in=PREVIOUS_ELIGIBLE_STATUSES,
            school_class__level__order=source_order,
        )
        .exclude(student_id__in=already_enrolled)
        .select_related(
            "student",
            "school_class",
            "school_class__level",
            "academic_year",
        )
        .order_by("student__nom", "student__postnom", "student__prenom")
    )


def assert_can_reenroll(
    *,
    previous_enrollment: Enrollment,
    target_class: SchoolClass,
) -> None:
    if previous_enrollment.status not in PREVIOUS_ELIGIBLE_STATUSES:
        raise SecretariatError("Seule une inscription validée ou clôturée peut être réinscrite.")

    previous_year = get_previous_closed_year(target_class.academic_year)
    if previous_year is None:
        raise SecretariatError(
            "Aucune année scolaire précédente clôturée n'est disponible pour la réinscription."
        )
    if previous_enrollment.academic_year_id != previous_year.pk:
        raise SecretariatError(
            "La réinscription concerne uniquement les élèves de l'année scolaire précédente clôturée."
        )

    source_order = source_level_order_for(target_class)
    if source_order is None:
        raise SecretariatError(
            "Cette classe est le premier niveau : utilisez une inscription, pas une réinscription."
        )

    previous_level = previous_enrollment.school_class.level
    if previous_level.order != source_order:
        raise SecretariatError(
            "On ne peut réinscrire qu'un élève provenant de la classe immédiatement inférieure "
            f"(attendu : niveau d'ordre {source_order}, reçu : {previous_level.order})."
        )

    if target_class.academic_year_id == previous_enrollment.academic_year_id:
        raise SecretariatError("La réinscription doit concerner une nouvelle année scolaire.")


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
    previous_enrollment = Enrollment.objects.select_for_update().select_related(
        "student",
        "school_class",
        "school_class__level",
        "academic_year",
    ).get(pk=previous_enrollment.pk)
    target_class = SchoolClass.objects.select_related("academic_year", "level").get(pk=target_class.pk)

    assert_can_reenroll(
        previous_enrollment=previous_enrollment,
        target_class=target_class,
    )

    enrollment = create_enrollment(
        student=previous_enrollment.student,
        school_class=target_class,
        enrollment_type=Enrollment.EnrollmentType.RENEWAL,
        force_over_capacity=force_over_capacity,
        actor=actor,
        request=request,
        skip_reenrollment_guard=True,
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
