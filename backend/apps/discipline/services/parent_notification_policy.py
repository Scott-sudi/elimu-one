"""Central policy for discipline events visible to parents."""

from __future__ import annotations

from collections.abc import Iterable

from apps.discipline.models import (
    AbsenceJustification,
    DailyAttendance,
    DisciplinaryIncident,
    DisciplinaryMeasure,
    ExitAuthorization,
    ParentSummons,
)

ATTENDANCE_PARENT_STATUSES = frozenset(DailyAttendance.Status.values)
INCIDENT_PARENT_STATUSES = frozenset(
    {
        DisciplinaryIncident.Status.CONFIRMED,
        DisciplinaryIncident.Status.CLOSED,
    }
)
MEASURE_PARENT_STATUSES = frozenset(
    {
        DisciplinaryMeasure.Status.VALIDATED,
        DisciplinaryMeasure.Status.IN_PROGRESS,
        DisciplinaryMeasure.Status.EXECUTED,
        DisciplinaryMeasure.Status.CLOSED,
    }
)
SUMMONS_PARENT_STATUSES = frozenset(
    {
        ParentSummons.Status.SENT,
        ParentSummons.Status.RECEIVED,
        ParentSummons.Status.CONFIRMED,
        ParentSummons.Status.PRESENT,
        ParentSummons.Status.ABSENT,
        ParentSummons.Status.POSTPONED,
        ParentSummons.Status.CANCELLED,
        ParentSummons.Status.CLOSED,
        ParentSummons.Status.ARCHIVED,
    }
)
EXIT_PARENT_STATUSES = frozenset(
    {
        ExitAuthorization.Status.AUTHORIZED,
        ExitAuthorization.Status.EXITED,
        ExitAuthorization.Status.RETURNED,
    }
)
JUSTIFICATION_PARENT_STATUSES = frozenset(
    {
        AbsenceJustification.Status.ACCEPTED,
        AbsenceJustification.Status.REJECTED,
    }
)

PARENT_STATUSES_BY_KIND = {
    "attendance": ATTENDANCE_PARENT_STATUSES,
    "incident": INCIDENT_PARENT_STATUSES,
    "measure": MEASURE_PARENT_STATUSES,
    "summons": SUMMONS_PARENT_STATUSES,
    "exit": EXIT_PARENT_STATUSES,
    "justification": JUSTIFICATION_PARENT_STATUSES,
}

SOURCE_BY_KIND = {
    "attendance": "discipline_attendance",
    "incident": "discipline_incident",
    "measure": "discipline_measure",
    "summons": "discipline_summons",
    "exit": "discipline_exit",
    "justification": "discipline_justification",
}


def is_parent_visible(kind: str, status: str) -> bool:
    return status in PARENT_STATUSES_BY_KIND.get(kind, ())


def notification_variant(
    *,
    kind: str,
    current_status: str,
    previous_status: str | None,
    created: bool,
    meaningful_changed: bool,
) -> str | None:
    """Return ``new``/``updated`` when this save warrants a parent event."""
    if not is_parent_visible(kind, current_status):
        return None
    if created or not is_parent_visible(kind, previous_status or ""):
        return "new"
    if previous_status != current_status or meaningful_changed:
        return "updated"
    return None


def meaningful_fields_changed(
    instance,
    previous: dict | None,
    fields: Iterable[str],
) -> bool:
    if not previous:
        return False
    return any(previous.get(field) != getattr(instance, field) for field in fields)

