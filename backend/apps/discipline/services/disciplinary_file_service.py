"""Build the student disciplinary file for a selected academic year."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db.models import Count, Q, Sum
from django.urls import reverse

from apps.discipline.models import (
    AbsenceJustification,
    ConductCategory,
    DailyAttendance,
    DisciplinaryIncident,
    DisciplinaryMeasure,
    ExitAuthorization,
    ParentSummons,
)
from apps.discipline.services.exceptions import DisciplineError
from apps.secretariat.models import AcademicYear, Enrollment, Student


@dataclass
class DisciplinaryFileData:
    reference: str
    student: Student
    enrollment: Enrollment
    academic_year: AcademicYear
    followup_status: str
    followup_status_label: str
    primary_guardian: object | None
    attendance_stats: dict
    recent_attendance: list
    incidents: list
    measures: list
    summonses: list
    timeline: list = field(default_factory=list)
    dossier_url: str = ""
    print_url: str = ""
    pdf_url: str = ""
    scanner_url: str = ""


def build_dossier_reference(*, academic_year: AcademicYear, student: Student) -> str:
    year_slug = (academic_year.label or "").replace(" ", "")
    matricule = (student.matricule or "SANS-MAT").upper().replace(" ", "")
    return f"DISC-{year_slug}-{matricule}"


def derive_followup_status(
    *,
    open_incidents: int,
    pending_summons: int,
    active_measures: int,
    late_count: int,
    unjustified_absences: int,
) -> tuple[str, str]:
    if open_incidents >= 3 or active_measures >= 2:
        return "GRAVE", "Dossier grave"
    if pending_summons > 0:
        return "CONVOCATION", "Convocation requise"
    if open_incidents > 0 or active_measures > 0:
        return "SUIVI", "Suivi requis"
    if late_count >= 5 or unjustified_absences >= 3:
        return "SURVEILLANCE", "À surveiller"
    return "NORMAL", "Situation normale"


def build_student_disciplinary_file(
    *,
    academic_year: AcademicYear,
    student_public_id,
) -> DisciplinaryFileData:
    enrollment = (
        Enrollment.objects.select_related(
            "student",
            "school_class",
            "school_class__level",
            "school_class__section",
            "school_class__option",
            "academic_year",
        )
        .filter(
            student__public_id=student_public_id,
            academic_year=academic_year,
            status=Enrollment.Status.VALIDATED,
        )
        .first()
    )
    if not enrollment:
        raise DisciplineError("Cet élève n'est pas inscrit dans l'année scolaire sélectionnée.")

    student = enrollment.student
    attendance_qs = DailyAttendance.objects.filter(academic_year=academic_year, student=student)
    stats_row = attendance_qs.aggregate(
        present=Count("id", filter=Q(status=DailyAttendance.Status.PRESENT)),
        late=Count("id", filter=Q(status=DailyAttendance.Status.LATE)),
        absent=Count("id", filter=Q(status=DailyAttendance.Status.ABSENT)),
        justified=Count("id", filter=Q(status=DailyAttendance.Status.JUSTIFIED_ABSENCE)),
        authorized_exit=Count("id", filter=Q(status=DailyAttendance.Status.AUTHORIZED_EXIT)),
        late_minutes=Sum("late_minutes"),
    )
    justified_ids = set(
        AbsenceJustification.objects.filter(
            attendance__academic_year=academic_year,
            attendance__student=student,
            status=AbsenceJustification.Status.ACCEPTED,
        ).values_list("attendance_id", flat=True)
    )
    unjustified = attendance_qs.filter(status=DailyAttendance.Status.ABSENT).exclude(id__in=justified_ids).count()

    incidents_qs = DisciplinaryIncident.objects.filter(
        academic_year=academic_year, student=student
    ).select_related("category", "school_class", "reported_by")
    open_incidents = incidents_qs.filter(
        status__in=[
            DisciplinaryIncident.Status.REPORTED,
            DisciplinaryIncident.Status.REVIEW,
            DisciplinaryIncident.Status.CONFIRMED,
        ]
    ).count()
    closed_incidents = incidents_qs.filter(
        status__in=[DisciplinaryIncident.Status.CLOSED, DisciplinaryIncident.Status.ARCHIVED]
    ).count()
    total_incidents = incidents_qs.count()
    positive_obs = incidents_qs.filter(
        category__observation_type=ConductCategory.ObservationType.POSITIVE
    ).count()
    negative_obs = incidents_qs.filter(
        category__observation_type=ConductCategory.ObservationType.NEGATIVE
    ).count()
    # Affichage : 3 derniers uniquement
    incidents = list(incidents_qs.order_by("-incident_date", "-created_at")[:3])

    measures_qs = DisciplinaryMeasure.objects.filter(
        incident__academic_year=academic_year, student=student
    ).select_related("measure_type", "incident")
    active_measures = measures_qs.filter(
        status__in=[DisciplinaryMeasure.Status.VALIDATED, DisciplinaryMeasure.Status.IN_PROGRESS]
    ).count()
    measures = list(measures_qs.order_by("-created_at")[:3])

    summons_qs = ParentSummons.objects.filter(
        academic_year=academic_year, student=student
    ).prefetch_related("target_guardians")
    total_summons = summons_qs.count()
    pending_summons = summons_qs.filter(
        status__in=[
            ParentSummons.Status.SCHEDULED,
            ParentSummons.Status.SENT,
            ParentSummons.Status.RECEIVED,
            ParentSummons.Status.CONFIRMED,
        ]
    ).count()
    summonses = list(summons_qs.order_by("-summon_date", "-created_at")[:3])

    followup_code, followup_label = derive_followup_status(
        open_incidents=open_incidents,
        pending_summons=pending_summons,
        active_measures=active_measures,
        late_count=stats_row["late"] or 0,
        unjustified_absences=unjustified,
    )

    primary_link = (
        student.guardian_links.select_related("guardian")
        .filter(is_primary=True)
        .first()
        or student.guardian_links.select_related("guardian").first()
    )

    # Tableau : derniers pointages seulement (les totaux annuels restent dans attendance_stats)
    recent_attendance = list(
        attendance_qs.select_related("enrollment__school_class").order_by("-date", "-updated_at")[:5]
    )

    reference = build_dossier_reference(academic_year=academic_year, student=student)
    pid = student.public_id
    return DisciplinaryFileData(
        reference=reference,
        student=student,
        enrollment=enrollment,
        academic_year=academic_year,
        followup_status=followup_code,
        followup_status_label=followup_label,
        primary_guardian=primary_link,
        attendance_stats={
            "present": stats_row["present"] or 0,
            "late": stats_row["late"] or 0,
            "absent": stats_row["absent"] or 0,
            "justified": stats_row["justified"] or 0,
            "unjustified": unjustified,
            "authorized_exit": stats_row["authorized_exit"] or 0,
            "late_minutes": int(stats_row["late_minutes"] or 0),
            "open_incidents": open_incidents,
            "closed_incidents": closed_incidents,
            "total_incidents": total_incidents,
            "pending_summons": pending_summons,
            "total_summons": total_summons,
            "active_measures": active_measures,
            "positive_observations": positive_obs,
            "negative_observations": negative_obs,
            "exits": ExitAuthorization.objects.filter(
                academic_year=academic_year, student=student
            ).count(),
        },
        recent_attendance=recent_attendance,
        incidents=incidents,
        measures=measures,
        summonses=summonses,
        timeline=[],
        dossier_url=reverse("discipline:student-disciplinary-file", kwargs={"public_id": pid}),
        print_url=reverse("discipline:student-disciplinary-file-print", kwargs={"public_id": pid}),
        pdf_url=reverse("discipline:student-disciplinary-file-pdf", kwargs={"public_id": pid}),
        scanner_url=reverse("discipline:attendance-daily") + "?mode=conduct&open=1",
    )
