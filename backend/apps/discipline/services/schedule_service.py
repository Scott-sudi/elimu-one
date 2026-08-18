"""Attendance schedule (vacation AM/PM) services."""

from __future__ import annotations

from datetime import time

from django.db import transaction

from apps.audit.models import AuditLog
from apps.discipline.models import AttendanceSchedule
from apps.discipline.services import audit_discipline_action
from apps.discipline.services.exceptions import DisciplineError
from apps.secretariat.models import AcademicYear, SchoolClass

DEFAULT_TIMES = {
    AttendanceSchedule.Vacation.MORNING: {
        "start_time": time(7, 30),
        "present_until": time(7, 45),
        "end_time": time(12, 30),
        "label": "Horaire avant-midi",
    },
    AttendanceSchedule.Vacation.AFTERNOON: {
        "start_time": time(12, 30),
        "present_until": time(12, 45),
        "end_time": time(18, 0),
        "label": "Horaire après-midi",
    },
}

# Fin de journée élargie pour tests / démo (pointage possible le soir).
RELAXED_END_TIME = time(23, 59)


def get_vacation_schedule(*, academic_year: AcademicYear, vacation: str) -> AttendanceSchedule | None:
    return (
        AttendanceSchedule.objects.filter(
            academic_year=academic_year,
            vacation=vacation,
            school_class__isnull=True,
            level__isnull=True,
            is_archived=False,
        )
        .order_by("-updated_at")
        .first()
    )


def build_vacation_form_initial(*, academic_year: AcademicYear, vacation: str) -> dict:
    defaults = DEFAULT_TIMES[vacation]
    schedule = get_vacation_schedule(academic_year=academic_year, vacation=vacation)
    classes = SchoolClass.objects.filter(
        academic_year=academic_year,
        is_active=True,
        vacation=vacation,
    )
    class_ids = list(classes.values_list("pk", flat=True))
    if schedule:
        return {
            "vacation": vacation,
            "start_time": schedule.start_time,
            "present_until": schedule.get_present_until(),
            "end_time": schedule.end_time or defaults["end_time"],
            "school_classes": class_ids,
        }
    return {
        "vacation": vacation,
        "start_time": defaults["start_time"],
        "present_until": defaults["present_until"],
        "end_time": defaults["end_time"],
        "school_classes": class_ids,
    }


@transaction.atomic
def save_vacation_schedule(
    *,
    academic_year: AcademicYear,
    vacation: str,
    start_time,
    present_until,
    end_time,
    school_classes,
    actor=None,
    request=None,
) -> AttendanceSchedule:
    if academic_year.is_closed:
        raise DisciplineError("L'année scolaire sélectionnée est clôturée.")
    if vacation not in AttendanceSchedule.Vacation.values:
        raise DisciplineError("Vacation invalide.")
    if present_until < start_time:
        raise DisciplineError("« Présent jusqu'à » doit être après le début des cours.")
    if end_time <= present_until:
        raise DisciplineError("La fin des cours doit être après la fin de tolérance.")

    selected_ids = {c.id for c in school_classes}
    year_classes = SchoolClass.objects.select_for_update().filter(
        academic_year=academic_year,
        is_active=True,
    )
    for school_class in year_classes:
        if school_class.id not in selected_ids:
            continue
        if school_class.academic_year_id != academic_year.id:
            raise DisciplineError("Une classe n'appartient pas à l'année sélectionnée.")

    defaults = DEFAULT_TIMES[vacation]
    schedule = get_vacation_schedule(academic_year=academic_year, vacation=vacation)
    if schedule is None:
        schedule = AttendanceSchedule(
            academic_year=academic_year,
            vacation=vacation,
            label=defaults["label"],
        )
    schedule.label = defaults["label"]
    schedule.start_time = start_time
    schedule.present_until = present_until
    schedule.end_time = end_time
    schedule.school_class = None
    schedule.level = None
    schedule.is_active = True
    schedule.is_archived = False
    schedule.sync_tolerance_from_present_until()
    schedule.save()

    other = (
        SchoolClass.Vacation.AFTERNOON
        if vacation == SchoolClass.Vacation.MORNING
        else SchoolClass.Vacation.MORNING
    )
    # Selected classes take this vacation; previously assigned but unchecked move to the other.
    year_classes.filter(id__in=selected_ids).update(vacation=vacation)
    year_classes.filter(vacation=vacation).exclude(id__in=selected_ids).update(vacation=other)

    audit_discipline_action(
        action=AuditLog.Action.DISCIPLINE_ATTENDANCE_UPDATED,
        instance=schedule,
        description=f"Horaire {schedule.get_vacation_display()} enregistré",
        actor=actor,
        request=request,
        new_values={
            "vacation": vacation,
            "start_time": str(start_time),
            "present_until": str(present_until),
            "end_time": str(end_time),
            "classes": len(selected_ids),
        },
    )
    return schedule


def ensure_default_attendance_schedules(
    *,
    academic_year: AcademicYear,
    actor=None,
    request=None,
    relaxed_end_time: bool = False,
) -> list[AttendanceSchedule]:
    """
    Create morning / afternoon schedules when missing.

    ``relaxed_end_time`` (demo / dev) extends « fin des cours » to 23:59 so
    evening QR tests are not blocked.
    """
    ensured: list[AttendanceSchedule] = []
    for vacation in AttendanceSchedule.Vacation.values:
        if get_vacation_schedule(academic_year=academic_year, vacation=vacation):
            continue
        defaults = DEFAULT_TIMES[vacation]
        end_time = RELAXED_END_TIME if relaxed_end_time else defaults["end_time"]
        classes = list(
            SchoolClass.objects.filter(
                academic_year=academic_year,
                is_active=True,
                vacation=vacation,
            )
        )
        if not classes and vacation == AttendanceSchedule.Vacation.MORNING:
            classes = list(
                SchoolClass.objects.filter(academic_year=academic_year, is_active=True)
            )
        schedule = save_vacation_schedule(
            academic_year=academic_year,
            vacation=vacation,
            start_time=defaults["start_time"],
            present_until=defaults["present_until"],
            end_time=end_time,
            school_classes=classes,
            actor=actor,
            request=request,
        )
        ensured.append(schedule)
    return ensured
