"""Class daily attendance workflow services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.discipline.models import ClassAttendanceSheet, DailyAttendance, StudentAttendanceRecord
from apps.discipline.services import audit_discipline_action
from apps.discipline.services.exceptions import DisciplineError
from apps.secretariat.models import AcademicYear, Enrollment, SchoolClass


@dataclass
class SheetTotals:
    total_students: int
    total_present: int
    total_absent: int
    total_unmarked: int


def validate_sheet_date(*, academic_year: AcademicYear, target_date: date) -> None:
    """
    Valide la date de feuille pour l'année sélectionnée.

    Si l'année n'est pas clôturée, on autorise aussi la date machine courante
    même après la date de fin officielle (période opérationnelle encore ouverte).
    """
    upper = academic_year.end_date
    if not academic_year.is_closed:
        today = timezone.localdate()
        if today > upper:
            upper = today
    if target_date < academic_year.start_date or target_date > upper:
        raise DisciplineError("La date est hors de l'année scolaire sélectionnée.")


def _class_for_enrollment_at_date(*, enrollment: Enrollment, target_date: date):
    transfers = enrollment.class_transfers.order_by("transfer_date", "created_at")
    first_transfer = transfers.first()
    if not first_transfer:
        return enrollment.school_class
    if target_date < first_transfer.transfer_date:
        return first_transfer.from_class
    latest = transfers.filter(transfer_date__lte=target_date).order_by("-transfer_date", "-created_at").first()
    if latest:
        return latest.to_class
    return enrollment.school_class


def active_enrollments_for_class_date(*, academic_year: AcademicYear, school_class: SchoolClass, target_date: date):
    validate_sheet_date(academic_year=academic_year, target_date=target_date)
    enrollments = (
        Enrollment.objects.filter(
            academic_year=academic_year,
            status=Enrollment.Status.VALIDATED,
        )
        .select_related("student", "school_class")
        .prefetch_related("class_transfers")
        .order_by("student__nom", "student__prenom")
    )
    matched = []
    for enrollment in enrollments:
        effective_class = _class_for_enrollment_at_date(enrollment=enrollment, target_date=target_date)
        if effective_class and effective_class.id == school_class.id:
            matched.append(enrollment)
    return matched


@transaction.atomic
def get_or_create_sheet(
    *,
    academic_year: AcademicYear,
    school_class: SchoolClass,
    target_date: date,
    actor,
) -> ClassAttendanceSheet:
    validate_sheet_date(academic_year=academic_year, target_date=target_date)
    if school_class.academic_year_id != academic_year.id:
        raise DisciplineError("La classe n'appartient pas à l'année scolaire sélectionnée.")
    sheet, created = ClassAttendanceSheet.objects.select_for_update().get_or_create(
        academic_year=academic_year,
        school_class=school_class,
        date=target_date,
        defaults={"created_by": actor},
    )
    if created:
        _seed_records_from_enrollments(sheet=sheet, actor=actor)
        recompute_sheet_totals(sheet=sheet, save=True)
    return sheet


def _seed_records_from_enrollments(*, sheet: ClassAttendanceSheet, actor):
    enrollments = active_enrollments_for_class_date(
        academic_year=sheet.academic_year,
        school_class=sheet.school_class,
        target_date=sheet.date,
    )
    existing = set(sheet.records.values_list("enrollment_id", flat=True))
    to_create = []
    for enrollment in enrollments:
        if enrollment.id in existing:
            continue
        to_create.append(
            StudentAttendanceRecord(
                sheet=sheet,
                enrollment=enrollment,
                student=enrollment.student,
                status=StudentAttendanceRecord.Status.UNMARKED,
                presence_value=None,
                mention="",
                school_class=sheet.school_class,
                recorded_by=actor,
            )
        )
    if to_create:
        StudentAttendanceRecord.objects.bulk_create(to_create)


def recompute_sheet_totals(*, sheet: ClassAttendanceSheet, save: bool = False) -> SheetTotals:
    stats = sheet.records.aggregate(
        total=Count("id"),
        present=Count("id", filter=Q(status=StudentAttendanceRecord.Status.PRESENT)),
        absent=Count("id", filter=Q(status=StudentAttendanceRecord.Status.ABSENT)),
        unmarked=Count("id", filter=Q(status=StudentAttendanceRecord.Status.UNMARKED)),
    )
    totals = SheetTotals(
        total_students=stats["total"] or 0,
        total_present=stats["present"] or 0,
        total_absent=stats["absent"] or 0,
        total_unmarked=stats["unmarked"] or 0,
    )
    if save:
        sheet.total_students = totals.total_students
        sheet.total_present = totals.total_present
        sheet.total_absent = totals.total_absent
        sheet.total_unmarked = totals.total_unmarked
        sheet.save(update_fields=["total_students", "total_present", "total_absent", "total_unmarked", "updated_at"])
    return totals


@transaction.atomic
def save_sheet_draft(
    *,
    sheet: ClassAttendanceSheet,
    statuses_by_record_id: dict[int, str],
    actor,
    request=None,
):
    if sheet.status == ClassAttendanceSheet.Status.VALIDATED:
        raise DisciplineError("Feuille déjà validée. Utilisez la correction contrôlée.")
    if sheet.status == ClassAttendanceSheet.Status.CLOSED:
        raise DisciplineError("La feuille est clôturée et ne peut plus être modifiée.")

    valid_statuses = {
        StudentAttendanceRecord.Status.UNMARKED,
        StudentAttendanceRecord.Status.PRESENT,
        StudentAttendanceRecord.Status.ABSENT,
    }
    records = list(sheet.records.select_for_update())
    for record in records:
        raw = statuses_by_record_id.get(record.id)
        if raw is None:
            continue
        if raw not in valid_statuses:
            raise DisciplineError("Statut de présence invalide.")
        record.apply_status(raw)
        record.recorded_by = actor
    StudentAttendanceRecord.objects.bulk_update(
        records,
        ["status", "presence_value", "mention", "recorded_by", "updated_at"],
    )

    if sheet.status == ClassAttendanceSheet.Status.NOT_STARTED:
        sheet.status = ClassAttendanceSheet.Status.DRAFT
        sheet.save(update_fields=["status", "updated_at"])

    totals = recompute_sheet_totals(sheet=sheet, save=True)
    audit_discipline_action(
        action=AuditLog.Action.DISCIPLINE_ATTENDANCE_UPDATED,
        instance=sheet,
        description=f"Brouillon feuille {sheet.school_class.name} {sheet.date:%Y-%m-%d}",
        actor=actor,
        request=request,
        new_values={
            "status": sheet.status,
            "present": totals.total_present,
            "absent": totals.total_absent,
            "unmarked": totals.total_unmarked,
        },
    )
    return totals


def _sync_daily_from_sheet_record(
    *,
    record: StudentAttendanceRecord,
    sheet: ClassAttendanceSheet,
    actor,
) -> DailyAttendance:
    """Écrit le DailyAttendance métier à partir de la ligne de feuille (sans push)."""
    if record.status == StudentAttendanceRecord.Status.PRESENT:
        desired = DailyAttendance.Status.PRESENT
    else:
        desired = DailyAttendance.Status.ABSENT

    daily, created = DailyAttendance.objects.select_for_update().get_or_create(
        enrollment=record.enrollment,
        date=sheet.date,
        defaults={
            "academic_year": sheet.academic_year,
            "student": record.student,
            "status": desired,
            "source": DailyAttendance.Source.MANUAL,
            "recorded_by": actor,
            "late_minutes": 0,
        },
    )
    # Conserver un retard déjà pointé (QR) si la feuille dit « présent ».
    if (
        desired == DailyAttendance.Status.PRESENT
        and not created
        and daily.status == DailyAttendance.Status.LATE
        and daily.arrival_time is not None
    ):
        daily.modified_by = actor
        daily.save(update_fields=["modified_by", "updated_at"])
        return daily

    daily.academic_year = sheet.academic_year
    daily.student = record.student
    daily.status = desired
    daily.source = DailyAttendance.Source.MANUAL
    daily.modified_by = actor
    if desired == DailyAttendance.Status.ABSENT:
        daily.late_minutes = 0
        daily.arrival_time = None
    elif desired == DailyAttendance.Status.PRESENT and daily.arrival_time is None:
        daily.late_minutes = 0
    daily.save()
    return daily


def _notify_parents_after_sheet_validation(
    *,
    attendance_ids: list[int],
    updated: bool = False,
) -> None:
    """Push parents uniquement après validation de feuille."""

    def _run() -> None:
        try:
            from apps.api.parents_push import notify_guardians_of_attendance

            for pk in attendance_ids:
                att = (
                    DailyAttendance.objects.select_related("student", "enrollment")
                    .filter(pk=pk)
                    .first()
                )
                if att is not None:
                    notify_guardians_of_attendance(attendance=att, updated=updated)
        except Exception:
            pass

    transaction.on_commit(_run)


@transaction.atomic
def validate_sheet(
    *,
    sheet: ClassAttendanceSheet,
    actor,
    request=None,
):
    if sheet.status == ClassAttendanceSheet.Status.CLOSED:
        raise DisciplineError("La feuille est déjà clôturée.")

    unmarked_records = list(
        sheet.records.select_for_update()
        .select_related("enrollment", "student")
        .filter(status=StudentAttendanceRecord.Status.UNMARKED)
    )
    for record in unmarked_records:
        record.apply_status(StudentAttendanceRecord.Status.ABSENT)
        record.recorded_by = actor
    if unmarked_records:
        StudentAttendanceRecord.objects.bulk_update(
            unmarked_records,
            ["status", "presence_value", "mention", "recorded_by", "updated_at"],
        )

    # Après validation : synchroniser toute la feuille, puis notifier les parents.
    all_records = list(
        sheet.records.select_for_update().select_related("enrollment", "student")
    )
    attendance_ids: list[int] = []
    for record in all_records:
        daily = _sync_daily_from_sheet_record(record=record, sheet=sheet, actor=actor)
        from apps.discipline.services.parent_notification_policy import (
            ATTENDANCE_PARENT_STATUSES,
        )

        if daily.status in ATTENDANCE_PARENT_STATUSES:
            attendance_ids.append(daily.pk)

    totals = recompute_sheet_totals(sheet=sheet, save=False)
    sheet.status = ClassAttendanceSheet.Status.VALIDATED
    sheet.validated_by = actor
    sheet.validation_at = timezone.now()
    sheet.total_students = totals.total_students
    sheet.total_present = totals.total_present
    sheet.total_absent = totals.total_absent
    sheet.total_unmarked = totals.total_unmarked
    sheet.save(
        update_fields=[
            "status",
            "validated_by",
            "validation_at",
            "total_students",
            "total_present",
            "total_absent",
            "total_unmarked",
            "updated_at",
        ]
    )
    audit_discipline_action(
        action=AuditLog.Action.DISCIPLINE_ATTENDANCE_UPDATED,
        instance=sheet,
        description=f"Validation feuille {sheet.school_class.name} {sheet.date:%Y-%m-%d}",
        actor=actor,
        request=request,
        new_values={
            "status": sheet.status,
            "present": totals.total_present,
            "absent": totals.total_absent,
            "auto_absent": len(unmarked_records),
            "parent_notified": len(attendance_ids),
        },
    )
    _notify_parents_after_sheet_validation(attendance_ids=attendance_ids)
    return totals


@transaction.atomic
def auto_close_elapsed_sheets(
    *,
    academic_year: AcademicYear,
    actor=None,
    request=None,
) -> int:
    """
    Auto-close past attendance sheets (date < today) so they become archives.
    Any remaining UNMARKED lines are converted to ABSENT before closure.
    """
    today = timezone.localdate()
    sheets = list(
        ClassAttendanceSheet.objects.select_for_update()
        .filter(academic_year=academic_year, date__lt=today)
        .exclude(status=ClassAttendanceSheet.Status.CLOSED)
    )
    if not sheets:
        return 0

    closed_count = 0
    for sheet in sheets:
        StudentAttendanceRecord.objects.filter(
            sheet=sheet,
            status=StudentAttendanceRecord.Status.UNMARKED,
        ).update(
            status=StudentAttendanceRecord.Status.ABSENT,
            presence_value=0,
            mention="ABS",
            recorded_by=actor,
        )
        totals = recompute_sheet_totals(sheet=sheet, save=False)
        now = timezone.now()
        if not sheet.validation_at:
            sheet.validation_at = now
        if sheet.validated_by_id is None and actor is not None:
            sheet.validated_by = actor
        sheet.status = ClassAttendanceSheet.Status.CLOSED
        sheet.closed_at = now
        if sheet.closed_by_id is None and actor is not None:
            sheet.closed_by = actor
        sheet.total_students = totals.total_students
        sheet.total_present = totals.total_present
        sheet.total_absent = totals.total_absent
        sheet.total_unmarked = totals.total_unmarked
        sheet.save(
            update_fields=[
                "status",
                "validation_at",
                "validated_by",
                "closed_at",
                "closed_by",
                "total_students",
                "total_present",
                "total_absent",
                "total_unmarked",
                "updated_at",
            ]
        )
        DailyAttendance.objects.filter(
            academic_year=academic_year,
            enrollment__school_class=sheet.school_class,
            date=sheet.date,
        ).update(is_day_closed=True)
        audit_discipline_action(
            action=AuditLog.Action.DISCIPLINE_ATTENDANCE_UPDATED,
            instance=sheet,
            description=f"Clôture automatique feuille {sheet.school_class.name} {sheet.date:%Y-%m-%d}",
            actor=actor,
            request=request,
            new_values={
                "status": sheet.status,
                "auto_closed": True,
                "present": totals.total_present,
                "absent": totals.total_absent,
            },
        )
        closed_count += 1
    return closed_count


@transaction.atomic
def correct_validated_record(
    *,
    record: StudentAttendanceRecord,
    new_status: str,
    reason: str,
    password: str,
    actor,
    request=None,
):
    if record.sheet.status not in {ClassAttendanceSheet.Status.VALIDATED, ClassAttendanceSheet.Status.CLOSED}:
        raise DisciplineError("La correction est autorisée seulement après validation.")
    if not reason.strip():
        raise DisciplineError("Le motif de correction est obligatoire.")
    if not actor.check_password(password or ""):
        raise DisciplineError("Mot de passe invalide.")
    old_values = {
        "status": record.status,
        "presence_value": record.presence_value,
        "mention": record.mention,
    }
    record.status = new_status
    record.observation = reason.strip()
    record.recorded_by = actor
    record.save()
    recompute_sheet_totals(sheet=record.sheet, save=True)

    # Resync + notif parent après correction contrôlée.
    daily = _sync_daily_from_sheet_record(record=record, sheet=record.sheet, actor=actor)
    _notify_parents_after_sheet_validation(attendance_ids=[daily.pk], updated=True)

    audit_discipline_action(
        action=AuditLog.Action.DISCIPLINE_ATTENDANCE_UPDATED,
        instance=record,
        description=f"Correction présence {record.student.matricule} ({record.sheet.date:%Y-%m-%d})",
        actor=actor,
        request=request,
        old_values=old_values,
        new_values={
            "status": record.status,
            "presence_value": record.presence_value,
            "mention": record.mention,
            "reason": reason.strip(),
        },
    )
