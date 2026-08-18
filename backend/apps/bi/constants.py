"""Shared BI constants and occupancy thresholds."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import DecimalField

from apps.discipline.models import DailyAttendance, DisciplinaryIncident, ParentSummons

ZERO = Decimal("0.00")
MONEY = DecimalField(max_digits=14, decimal_places=2)

LOW_COLLECTION_THRESHOLD = Decimal("50")

OPEN_INCIDENT_STATUSES = (
    DisciplinaryIncident.Status.REPORTED,
    DisciplinaryIncident.Status.REVIEW,
    DisciplinaryIncident.Status.CONFIRMED,
)

CLOSED_INCIDENT_STATUSES = (
    DisciplinaryIncident.Status.DISMISSED,
    DisciplinaryIncident.Status.CLOSED,
)

SEVERE_SEVERITIES = (
    DisciplinaryIncident.Severity.HIGH,
    DisciplinaryIncident.Severity.VERY_HIGH,
)

PENDING_SUMMONS_STATUSES = (
    ParentSummons.Status.SCHEDULED,
    ParentSummons.Status.SENT,
    ParentSummons.Status.RECEIVED,
    ParentSummons.Status.CONFIRMED,
)

PRESENT_LIKE = (
    DailyAttendance.Status.PRESENT,
    DailyAttendance.Status.LATE,
)

ABSENT_LIKE = (
    DailyAttendance.Status.ABSENT,
    DailyAttendance.Status.JUSTIFIED_ABSENCE,
    DailyAttendance.Status.SICK,
)

# Seuils d'occupation des classes (pourcentage).
OCCUPANCY_LOW = 50
OCCUPANCY_NEAR_FULL = 85


def occupancy_status(*, occupied: int, capacity: int) -> str:
    """Return French occupancy label for a class."""
    if capacity <= 0:
        return "Capacité indéfinie"
    rate = occupied * 100 / capacity
    if occupied > capacity:
        return "Capacité dépassée"
    if rate >= 100:
        return "Complète"
    if rate >= OCCUPANCY_NEAR_FULL:
        return "Presque complète"
    if rate >= OCCUPANCY_LOW:
        return "Occupation normale"
    return "Faiblement occupée"
