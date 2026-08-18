"""Attendance and QR pointage business services."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from django.db import transaction
from django.utils.dateparse import parse_date
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.utils import get_client_ip
from apps.discipline.models import AttendanceSchedule, AttendanceScanEvent, ClassAttendanceSheet, DailyAttendance, StudentAttendanceRecord
from apps.discipline.services import audit_discipline_action
from apps.discipline.services.exceptions import DisciplineError
from apps.secretariat.models import AcademicYear, Enrollment, SchoolClass, StudentCard
from .class_attendance_service import get_or_create_sheet, recompute_sheet_totals
from .student_identity_service import resolve_student_identity

QR_IDENTIFIER_RE = re.compile(r"(KAL-CARD-[0-9a-fA-F]+)")
DUPLICATE_WINDOW_SECONDS = 120


def _notify_guardians_after_attendance_commit(attendance_id: int) -> None:
    """
    Ancien hook immédiat — désactivé.

    Les parents reçoivent la notif seulement quand le gestionnaire
    valide la feuille du jour (class_attendance_service.validate_sheet).
    """
    return


@dataclass
class AttendancePointageResult:
    ok: bool
    message: str
    student_name: str = ""
    matricule: str = ""
    class_name: str = ""
    card_status: str = ""
    operation: str = ""
    attendance_status: str = ""
    arrival_time: str = ""
    exit_time: str = ""
    late_minutes: int = 0
    duplicate: bool = False
    operation_label: str = ""


def normalize_card_qr_payload(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise DisciplineError("Aucun code QR détecté.")
    match = QR_IDENTIFIER_RE.search(value)
    if match:
        return match.group(1)
    if value.upper().startswith("KAL-CARD-"):
        return value
    raise DisciplineError("QR invalide. Carte élève ELIMU attendue.")


def _resolve_schedule(enrollment: Enrollment) -> AttendanceSchedule | None:
    year = enrollment.academic_year
    school_class = enrollment.school_class
    class_specific = (
        AttendanceSchedule.objects.filter(
            academic_year=year,
            school_class=school_class,
            is_active=True,
            is_archived=False,
        )
        .order_by("-updated_at")
        .first()
    )
    if class_specific:
        return class_specific

    vacation = getattr(school_class, "vacation", "") or ""
    if vacation:
        by_vacation = (
            AttendanceSchedule.objects.filter(
                academic_year=year,
                vacation=vacation,
                school_class__isnull=True,
                level__isnull=True,
                is_active=True,
                is_archived=False,
            )
            .order_by("-updated_at")
            .first()
        )
        if by_vacation:
            return by_vacation

    by_level = (
        AttendanceSchedule.objects.filter(
            academic_year=year,
            level=school_class.level,
            school_class__isnull=True,
            is_active=True,
            is_archived=False,
        )
        .order_by("-updated_at")
        .first()
    )
    if by_level:
        return by_level

    return (
        AttendanceSchedule.objects.filter(
            academic_year=year,
            level__isnull=True,
            school_class__isnull=True,
            vacation="",
            is_active=True,
            is_archived=False,
        )
        .order_by("-updated_at")
        .first()
    )


def _arrival_local_time(arrival_dt: datetime):
    if timezone.is_aware(arrival_dt):
        return timezone.localtime(arrival_dt).time()
    return arrival_dt.time()


def _evaluate_arrival_status(enrollment: Enrollment, arrival_dt: datetime) -> tuple[str, int]:
    """
    Apply schedule rules:
    - until present_until (start + tolerance) → PRESENT
    - after present_until until end_time → LATE
    - after end_time → refused
    """
    schedule = _resolve_schedule(enrollment)
    if not schedule:
        return DailyAttendance.Status.PRESENT, 0

    local_time = _arrival_local_time(arrival_dt)
    if schedule.end_time and local_time > schedule.end_time:
        end_label = schedule.end_time.strftime("%H:%M")
        raise DisciplineError(
            f"Pointage refusé : les cours sont terminés pour cette vacation (fin à {end_label}). "
            "Ajustez les horaires dans Discipline → Horaires, ou pointez pendant la plage autorisée."
        )

    present_until = schedule.get_present_until()
    if local_time <= present_until:
        return DailyAttendance.Status.PRESENT, 0

    expected_dt = datetime.combine(arrival_dt.date(), present_until)
    expected_dt = timezone.make_aware(expected_dt, timezone.get_current_timezone())
    aware_arrival = arrival_dt
    if timezone.is_naive(aware_arrival):
        aware_arrival = timezone.make_aware(aware_arrival, timezone.get_current_timezone())
    minutes = max(int((aware_arrival - expected_dt).total_seconds() // 60), 0)
    return DailyAttendance.Status.LATE, minutes


def _late_minutes(enrollment: Enrollment, arrival_dt: datetime) -> int:
    _status, minutes = _evaluate_arrival_status(enrollment, arrival_dt)
    return minutes


def _record_scan_event(
    *,
    academic_year: AcademicYear,
    enrollment: Enrollment | None,
    event_type: str,
    result: str,
    message: str,
    scanned_at: datetime,
    qr_identifier: str,
    scanned_by=None,
    request=None,
) -> AttendanceScanEvent:
    student = enrollment.student if enrollment else None
    return AttendanceScanEvent.objects.create(
        academic_year=academic_year,
        enrollment=enrollment,
        student=student,
        event_type=event_type,
        result=result,
        message=message[:255],
        scanned_at=scanned_at,
        qr_identifier=qr_identifier,
        scanned_by=scanned_by,
        scanner_device=(request.META.get("HTTP_USER_AGENT", "")[:120] if request else ""),
        ip_address=get_client_ip(request) if request else None,
    )


def _duplicate_scan_exists(
    *,
    academic_year: AcademicYear,
    enrollment: Enrollment,
    event_type: str,
    scanned_at: datetime,
) -> bool:
    threshold = scanned_at - timezone.timedelta(seconds=DUPLICATE_WINDOW_SECONDS)
    return AttendanceScanEvent.objects.filter(
        academic_year=academic_year,
        enrollment=enrollment,
        event_type=event_type,
        result=AttendanceScanEvent.Result.SUCCESS,
        scanned_at__gte=threshold,
    ).exists()


@transaction.atomic
def register_qr_pointage(
    *,
    academic_year: AcademicYear,
    qr_payload: str,
    operation: str = "arrivee",
    actor=None,
    request=None,
    scanned_at: datetime | None = None,
) -> AttendancePointageResult:
    """Register attendance pointage. Only arrival/presence is supported (no exit)."""
    scanned_at = scanned_at or timezone.localtime()
    # Pointage Discipline = entrée uniquement (la sortie n'est plus gérée ici).
    operation = "arrivee"
    event_type = AttendanceScanEvent.EventType.ARRIVAL
    identifier = normalize_card_qr_payload(qr_payload)
    card = (
        StudentCard.objects.select_related(
            "student",
            "enrollment",
            "enrollment__academic_year",
            "enrollment__school_class",
        )
        .filter(qr_identifier=identifier)
        .first()
    )
    if card is None:
        _record_scan_event(
            academic_year=academic_year,
            enrollment=None,
            event_type=event_type,
            result=AttendanceScanEvent.Result.UNKNOWN_QR,
            message="Carte introuvable.",
            scanned_at=scanned_at,
            qr_identifier=identifier,
            scanned_by=actor,
            request=request,
        )
        raise DisciplineError("Carte introuvable pour ce QR.")

    if card.is_blocked or not card.is_active:
        _record_scan_event(
            academic_year=academic_year,
            enrollment=card.enrollment,
            event_type=event_type,
            result=AttendanceScanEvent.Result.BLOCKED_CARD,
            message=card.block_reason or "Carte bloquée/inactive.",
            scanned_at=scanned_at,
            qr_identifier=identifier,
            scanned_by=actor,
            request=request,
        )
        raise DisciplineError(card.block_reason or "Cette carte est bloquée.")

    enrollment = card.enrollment
    if enrollment.academic_year_id != academic_year.id:
        card_year = enrollment.academic_year
        _record_scan_event(
            academic_year=academic_year,
            enrollment=enrollment,
            event_type=event_type,
            result=AttendanceScanEvent.Result.WRONG_YEAR,
            message="Carte hors année scolaire sélectionnée.",
            scanned_at=scanned_at,
            qr_identifier=identifier,
            scanned_by=actor,
            request=request,
        )
        raise DisciplineError(
            "Cette carte appartient à l'année scolaire "
            f"«{card_year.label}», alors que vous travaillez sur «{academic_year.label}». "
            "Changez d'année scolaire (menu Discipline) ou utilisez la carte de l'année en cours."
        )
    if enrollment.status != Enrollment.Status.VALIDATED:
        _record_scan_event(
            academic_year=academic_year,
            enrollment=enrollment,
            event_type=event_type,
            result=AttendanceScanEvent.Result.WRONG_YEAR,
            message="Inscription inactive.",
            scanned_at=scanned_at,
            qr_identifier=identifier,
            scanned_by=actor,
            request=request,
        )
        raise DisciplineError("Élève non inscrit dans l'année scolaire sélectionnée.")

    try:
        arrival_status, minutes = _evaluate_arrival_status(enrollment, scanned_at)
    except DisciplineError as exc:
        _record_scan_event(
            academic_year=academic_year,
            enrollment=enrollment,
            event_type=event_type,
            result=AttendanceScanEvent.Result.ERROR,
            message=str(exc),
            scanned_at=scanned_at,
            qr_identifier=identifier,
            scanned_by=actor,
            request=request,
        )
        raise

    if _duplicate_scan_exists(
        academic_year=academic_year,
        enrollment=enrollment,
        event_type=event_type,
        scanned_at=scanned_at,
    ):
        _record_scan_event(
            academic_year=academic_year,
            enrollment=enrollment,
            event_type=event_type,
            result=AttendanceScanEvent.Result.DUPLICATE,
            message="Doublon détecté.",
            scanned_at=scanned_at,
            qr_identifier=identifier,
            scanned_by=actor,
            request=request,
        )
        return AttendancePointageResult(
            ok=True,
            duplicate=True,
            message="Ce pointage vient déjà d'être enregistré.",
            student_name=enrollment.student.__str__().split("—", 1)[-1].strip(),
            matricule=enrollment.student.matricule,
            class_name=enrollment.school_class.name,
            operation=operation,
            card_status="active",
            operation_label="Arrivée",
        )

    attendance, created = DailyAttendance.objects.select_for_update().get_or_create(
        enrollment=enrollment,
        date=scanned_at.date(),
        defaults={
            "academic_year": academic_year,
            "student": enrollment.student,
            "source": DailyAttendance.Source.QR,
            "recorded_by": actor,
            # Pas PRESENT par défaut : évite notif/inbox avant validation feuille.
            "status": DailyAttendance.Status.ABSENT,
        },
    )
    # Already arrived today → no second arrival / no exit.
    if attendance.arrival_time is not None or (
        not created
        and attendance.status
        in {
            DailyAttendance.Status.PRESENT,
            DailyAttendance.Status.LATE,
        }
    ):
        return AttendancePointageResult(
            ok=True,
            duplicate=True,
            message="Ce pointage vient déjà d'être enregistré.",
            student_name=" ".join(
                p for p in (enrollment.student.nom, enrollment.student.postnom, enrollment.student.prenom) if p
            ),
            matricule=enrollment.student.matricule,
            class_name=enrollment.school_class.name,
            operation=operation,
            attendance_status=attendance.get_status_display(),
            arrival_time=attendance.arrival_time.strftime("%H:%M") if attendance.arrival_time else "",
            late_minutes=attendance.late_minutes,
            card_status="active",
            operation_label="Arrivée",
        )

    attendance.academic_year = academic_year
    attendance.student = enrollment.student
    attendance.source = DailyAttendance.Source.QR
    attendance.modified_by = actor
    attendance.arrival_time = scanned_at.timetz().replace(tzinfo=None)
    attendance.late_minutes = minutes
    attendance.status = arrival_status
    if minutes > 0:
        message = f"Arrivée enregistrée avec retard ({minutes} min)."
    else:
        message = f"Arrivée enregistrée à {scanned_at:%H h %M}."

    attendance.save()
    _notify_guardians_after_attendance_commit(attendance.pk)

    event = _record_scan_event(
        academic_year=academic_year,
        enrollment=enrollment,
        event_type=event_type,
        result=AttendanceScanEvent.Result.SUCCESS,
        message=message,
        scanned_at=scanned_at,
        qr_identifier=identifier,
        scanned_by=actor,
        request=request,
    )
    audit_discipline_action(
        action=AuditLog.Action.DISCIPLINE_ATTENDANCE_SCANNED,
        instance=event,
        description=f"Pointage arrivée de {enrollment.student.matricule}",
        actor=actor,
        request=request,
        new_values={
            "operation": operation,
            "matricule": enrollment.student.matricule,
            "classe": enrollment.school_class.name,
            "status": attendance.status,
            "date": str(attendance.date),
            "late_minutes": attendance.late_minutes,
        },
    )

    return AttendancePointageResult(
        ok=True,
        message=message,
        student_name=" ".join(
            p for p in (enrollment.student.nom, enrollment.student.postnom, enrollment.student.prenom) if p
        ),
        matricule=enrollment.student.matricule,
        class_name=enrollment.school_class.name,
        card_status="active",
        operation=operation,
        attendance_status=attendance.get_status_display(),
        arrival_time=attendance.arrival_time.strftime("%H:%M") if attendance.arrival_time else "",
        exit_time="",
        late_minutes=attendance.late_minutes,
        operation_label="Arrivée",
    )


def _sync_sheet_record_from_daily(*, academic_year: AcademicYear, enrollment: Enrollment, target_date: date, actor):
    school_class = enrollment.school_class
    sheet = get_or_create_sheet(
        academic_year=academic_year,
        school_class=school_class,
        target_date=target_date,
        actor=actor,
    )
    if sheet.status == ClassAttendanceSheet.Status.CLOSED:
        raise DisciplineError("Cette journée est archivée. Le pointage n'est plus possible.")
    record = sheet.records.filter(enrollment=enrollment).first()
    if not record:
        record = StudentAttendanceRecord.objects.create(
            sheet=sheet,
            enrollment=enrollment,
            student=enrollment.student,
            school_class=school_class,
            status=StudentAttendanceRecord.Status.ABSENT,
            presence_value=0,
            mention="ABS",
            recorded_by=actor,
        )
    daily = DailyAttendance.objects.filter(enrollment=enrollment, date=target_date).first()
    if not daily:
        return
    if daily.status == DailyAttendance.Status.ABSENT:
        record.status = StudentAttendanceRecord.Status.ABSENT
        record.presence_value = 0
        record.mention = "ABS"
    elif daily.status == DailyAttendance.Status.LATE:
        record.status = StudentAttendanceRecord.Status.PRESENT
        record.presence_value = 1
        record.mention = "OK"
    elif daily.status in {DailyAttendance.Status.PRESENT, DailyAttendance.Status.AUTHORIZED_EXIT}:
        record.status = StudentAttendanceRecord.Status.PRESENT
        record.presence_value = 1
        record.mention = "OK"
    else:
        record.status = StudentAttendanceRecord.Status.ABSENT
        record.presence_value = 0
        record.mention = "ABS"
    record.recorded_by = actor
    record.save()
    recompute_sheet_totals(sheet=sheet, save=True)


@transaction.atomic
def register_identifier_pointage(
    *,
    academic_year: AcademicYear,
    identifier: str,
    actor=None,
    request=None,
    class_public_id=None,
    sheet_date=None,
) -> AttendancePointageResult:
    """Pointage Discipline : entrée/présence uniquement (pas de sortie)."""
    if academic_year.is_closed:
        raise DisciplineError("L'année scolaire sélectionnée est clôturée.")
    resolved = resolve_student_identity(academic_year=academic_year, identifier=identifier)
    enrollment = resolved.enrollment

    if class_public_id:
        selected_class = SchoolClass.objects.filter(public_id=class_public_id, academic_year=academic_year).first()
        if not selected_class:
            raise DisciplineError("Classe cible introuvable.")
        if enrollment.school_class_id != selected_class.id:
            raise DisciplineError("Cet élève n'appartient pas à la classe sélectionnée.")

    now_dt = timezone.localtime()
    target_date = now_dt.date()
    if sheet_date:
        parsed = parse_date(str(sheet_date))
        if not parsed:
            raise DisciplineError("Date de feuille invalide.")
        target_date = parsed

    # Même règle que validate_sheet_date : année ouverte => date machine autorisée.
    upper = academic_year.end_date
    if not academic_year.is_closed and now_dt.date() > upper:
        upper = now_dt.date()
    if target_date < academic_year.start_date or target_date > upper:
        raise DisciplineError("La date est hors de l'année scolaire sélectionnée.")

    # Journée passée = archive : plus de pointage.
    if target_date < now_dt.date():
        raise DisciplineError("Cette journée est archivée. Le pointage n'est plus possible.")

    try:
        arrival_status, minutes = _evaluate_arrival_status(enrollment, now_dt)
    except DisciplineError as exc:
        _record_scan_event(
            academic_year=academic_year,
            enrollment=enrollment,
            event_type=AttendanceScanEvent.EventType.ARRIVAL,
            result=AttendanceScanEvent.Result.ERROR,
            message=str(exc),
            scanned_at=now_dt,
            qr_identifier=resolved.identifier,
            scanned_by=actor,
            request=request,
        )
        raise

    existing = DailyAttendance.objects.filter(enrollment=enrollment, date=target_date).first()
    if existing and (
        existing.arrival_time is not None
        or existing.status in {DailyAttendance.Status.PRESENT, DailyAttendance.Status.LATE}
    ):
        return AttendancePointageResult(
            ok=True,
            duplicate=True,
            message="Ce pointage vient déjà d'être enregistré.",
            student_name=" ".join(
                p for p in (enrollment.student.nom, enrollment.student.postnom, enrollment.student.prenom) if p
            ),
            matricule=enrollment.student.matricule,
            class_name=enrollment.school_class.name,
            operation="arrivee",
            attendance_status=existing.get_status_display(),
            arrival_time=existing.arrival_time.strftime("%H:%M") if existing.arrival_time else "",
            late_minutes=existing.late_minutes,
            operation_label="Arrivée",
        )

    event_type = AttendanceScanEvent.EventType.ARRIVAL
    if _duplicate_scan_exists(
        academic_year=academic_year,
        enrollment=enrollment,
        event_type=event_type,
        scanned_at=now_dt,
    ):
        return AttendancePointageResult(
            ok=True,
            duplicate=True,
            message="Ce pointage vient déjà d'être enregistré.",
            student_name=" ".join(
                p for p in (enrollment.student.nom, enrollment.student.postnom, enrollment.student.prenom) if p
            ),
            matricule=enrollment.student.matricule,
            class_name=enrollment.school_class.name,
            operation="arrivee",
            attendance_status=(existing.get_status_display() if existing else ""),
            operation_label="Arrivée",
        )

    source = DailyAttendance.Source.QR if resolved.card else DailyAttendance.Source.MANUAL
    attendance, _ = DailyAttendance.objects.select_for_update().get_or_create(
        enrollment=enrollment,
        date=target_date,
        defaults={
            "academic_year": academic_year,
            "student": enrollment.student,
            "source": source,
            "recorded_by": actor,
            "status": DailyAttendance.Status.ABSENT,
        },
    )
    attendance.academic_year = academic_year
    attendance.student = enrollment.student
    attendance.source = source
    attendance.modified_by = actor
    attendance.arrival_time = now_dt.timetz().replace(tzinfo=None)
    attendance.late_minutes = minutes
    attendance.status = arrival_status
    message = (
        f"Arrivée enregistrée avec retard ({minutes} min)."
        if minutes > 0
        else f"Arrivée enregistrée à {now_dt:%H h %M}."
    )
    attendance.save()
    _notify_guardians_after_attendance_commit(attendance.pk)

    event = _record_scan_event(
        academic_year=academic_year,
        enrollment=enrollment,
        event_type=event_type,
        result=AttendanceScanEvent.Result.SUCCESS,
        message=message,
        scanned_at=now_dt,
        qr_identifier=resolved.identifier,
        scanned_by=actor,
        request=request,
    )
    audit_discipline_action(
        action=AuditLog.Action.DISCIPLINE_ATTENDANCE_SCANNED,
        instance=event,
        description=f"Pointage arrivée de {enrollment.student.matricule}",
        actor=actor,
        request=request,
        new_values={
            "operation": "arrivee",
            "matricule": enrollment.student.matricule,
            "classe": enrollment.school_class.name,
            "status": attendance.status,
            "date": str(attendance.date),
            "late_minutes": attendance.late_minutes,
            "identifier_type": resolved.identifier_type,
        },
    )
    result = AttendancePointageResult(
        ok=True,
        message=message,
        student_name=" ".join(
            p for p in (enrollment.student.nom, enrollment.student.postnom, enrollment.student.prenom) if p
        ),
        matricule=enrollment.student.matricule,
        class_name=enrollment.school_class.name,
        card_status="active",
        operation="arrivee",
        attendance_status=attendance.get_status_display(),
        arrival_time=attendance.arrival_time.strftime("%H:%M") if attendance.arrival_time else "",
        exit_time="",
        late_minutes=attendance.late_minutes,
        operation_label="Arrivée",
    )
    _sync_sheet_record_from_daily(
        academic_year=academic_year,
        enrollment=enrollment,
        target_date=target_date,
        actor=actor,
    )
    return result


@transaction.atomic
def register_manual_attendance(
    *,
    academic_year: AcademicYear,
    enrollment: Enrollment,
    status: str,
    actor=None,
    note: str = "",
    for_date: date | None = None,
    request=None,
) -> DailyAttendance:
    if enrollment.academic_year_id != academic_year.id:
        raise DisciplineError("Inscription hors année scolaire sélectionnée.")
    if enrollment.status != Enrollment.Status.VALIDATED:
        raise DisciplineError("Inscription non validée.")

    target_date = for_date or timezone.localdate()
    attendance, _ = DailyAttendance.objects.select_for_update().get_or_create(
        enrollment=enrollment,
        date=target_date,
        defaults={
            "academic_year": academic_year,
            "student": enrollment.student,
            "recorded_by": actor,
            "status": DailyAttendance.Status.ABSENT,
        },
    )
    old_status = attendance.status
    attendance.status = status
    attendance.source = DailyAttendance.Source.MANUAL
    attendance.modified_by = actor
    if note:
        attendance.note = note
    if status != DailyAttendance.Status.LATE:
        attendance.late_minutes = 0
    attendance.save()

    notify_statuses = {
        DailyAttendance.Status.PRESENT,
        DailyAttendance.Status.LATE,
        DailyAttendance.Status.ABSENT,
    }
    if status in notify_statuses and old_status != status:
        _notify_guardians_after_attendance_commit(attendance.pk)

    audit_discipline_action(
        action=AuditLog.Action.DISCIPLINE_ATTENDANCE_UPDATED,
        instance=attendance,
        description=f"Marquage manuel de présence pour {enrollment.student.matricule}",
        actor=actor,
        request=request,
        old_values={"status": old_status},
        new_values={"status": attendance.status, "date": str(attendance.date)},
    )
    return attendance

