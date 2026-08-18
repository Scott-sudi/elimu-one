"""Attendance analytics for the Préfet BI module."""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.bi.constants import ABSENT_LIKE, PRESENT_LIKE
from apps.bi.filters import BiFilters
from apps.bi.selectors.attendance_selectors import attendance_qs
from apps.discipline.models import DailyAttendance
from apps.secretariat.models import AcademicYear


def build_attendance_analytics(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> dict[str, Any]:
    filters = filters or BiFilters()
    qs = attendance_qs(academic_year, filters)

    agg = qs.aggregate(
        total=Count("id"),
        present=Count("id", filter=Q(status=DailyAttendance.Status.PRESENT)),
        late=Count("id", filter=Q(status=DailyAttendance.Status.LATE)),
        present_like=Count("id", filter=Q(status__in=PRESENT_LIKE)),
        absent=Count("id", filter=Q(status=DailyAttendance.Status.ABSENT)),
        justified=Count(
            "id", filter=Q(status=DailyAttendance.Status.JUSTIFIED_ABSENCE)
        ),
        sick=Count("id", filter=Q(status=DailyAttendance.Status.SICK)),
        exempted=Count("id", filter=Q(status=DailyAttendance.Status.EXEMPTED)),
        authorized_exit=Count(
            "id", filter=Q(status=DailyAttendance.Status.AUTHORIZED_EXIT)
        ),
        late_minutes=Sum("late_minutes"),
    )
    total = agg["total"] or 0
    present_like = agg["present_like"] or 0
    taux_presence = round(present_like * 100 / total, 1) if total else None
    absences_injustifiees = agg["absent"] or 0
    absences_justifiees = (agg["justified"] or 0) + (agg["sick"] or 0)

    by_status = list(
        qs.values("status").annotate(nb=Count("id")).order_by("status")
    )
    status_labels = dict(DailyAttendance.Status.choices)

    monthly = list(
        qs.annotate(period=TruncMonth("date"))
        .values("period")
        .annotate(
            total=Count("id"),
            present_like=Count("id", filter=Q(status__in=PRESENT_LIKE)),
            late=Count("id", filter=Q(status=DailyAttendance.Status.LATE)),
            absent_like=Count("id", filter=Q(status__in=ABSENT_LIKE)),
        )
        .order_by("period")
    )

    by_class = list(
        qs.values(
            "enrollment__school_class_id",
            "enrollment__school_class__name",
        )
        .annotate(
            total=Count("id"),
            present_like=Count("id", filter=Q(status__in=PRESENT_LIKE)),
            late=Count("id", filter=Q(status=DailyAttendance.Status.LATE)),
            absent=Count(
                "id",
                filter=Q(
                    status__in=(
                        DailyAttendance.Status.ABSENT,
                        DailyAttendance.Status.JUSTIFIED_ABSENCE,
                        DailyAttendance.Status.SICK,
                    )
                ),
            ),
        )
        .order_by("enrollment__school_class__name")
    )
    class_rows = []
    for row in by_class:
        t = row["total"] or 0
        class_rows.append(
            {
                "class_id": row["enrollment__school_class_id"],
                "name": row["enrollment__school_class__name"],
                "total": t,
                "present_like": row["present_like"],
                "late": row["late"],
                "absent": row["absent"],
                "taux_presence": round(row["present_like"] * 100 / t, 1) if t else None,
            }
        )

    followup = list(
        qs.filter(
            status__in=(
                DailyAttendance.Status.ABSENT,
                DailyAttendance.Status.LATE,
                DailyAttendance.Status.JUSTIFIED_ABSENCE,
            )
        )
        .values(
            "student_id",
            "student__matricule",
            "student__nom",
            "student__prenom",
            "enrollment__school_class__name",
        )
        .annotate(
            absences=Count("id", filter=Q(status=DailyAttendance.Status.ABSENT)),
            retards=Count("id", filter=Q(status=DailyAttendance.Status.LATE)),
            justified=Count(
                "id", filter=Q(status=DailyAttendance.Status.JUSTIFIED_ABSENCE)
            ),
        )
        .filter(Q(absences__gte=3) | Q(retards__gte=5))
        .order_by("-absences", "-retards")[:50]
    )

    return {
        "kpis": {
            "enregistrements": total,
            "presents": agg["present"] or 0,
            "retards": agg["late"] or 0,
            "absences_injustifiees": absences_injustifiees,
            "absences_justifiees": absences_justifiees,
            "minutes_retard": agg["late_minutes"] or 0,
            "sorties_autorisees": agg["authorized_exit"] or 0,
            "taux_presence": taux_presence,
        },
        "charts": {
            "status": {
                "labels": [
                    status_labels.get(r["status"], r["status"]) for r in by_status
                ],
                "series": [{"name": "Pointages", "data": [r["nb"] for r in by_status]}],
            },
            "late": {
                "labels": [
                    row["period"].strftime("%Y-%m") if row["period"] else ""
                    for row in monthly
                ],
                "series": [
                    {
                        "name": "Retards",
                        "data": [row["late"] for row in monthly],
                    },
                    {
                        "name": "Absences",
                        "data": [row["absent_like"] for row in monthly],
                    },
                ],
            },
            "trend": {
                "labels": [
                    row["period"].strftime("%Y-%m") if row["period"] else ""
                    for row in monthly
                ],
                "series": [
                    {
                        "name": "Taux de présence (%)",
                        "data": [
                            round(row["present_like"] * 100 / row["total"], 1)
                            if row["total"]
                            else 0
                            for row in monthly
                        ],
                    }
                ],
            },
            "by_class": {
                "labels": [r["name"] for r in class_rows],
                "series": [
                    {
                        "name": "Taux de présence (%)",
                        "data": [
                            r["taux_presence"] if r["taux_presence"] is not None else 0
                            for r in class_rows
                        ],
                    }
                ],
            },
        },
        "tables": {
            "by_class": class_rows,
            "followup": followup,
            "by_status": [
                {
                    "status": r["status"],
                    "label": status_labels.get(r["status"], r["status"]),
                    "nb": r["nb"],
                }
                for r in by_status
            ],
        },
        "filters": filters.as_dict(),
        "generated_at": timezone.now(),
    }
