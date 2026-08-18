"""Parents mobile API — modules par enfant (présence, discipline, finance)."""

from __future__ import annotations

from decimal import Decimal

from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.api.views import envelope
from apps.discipline.models import (
    DailyAttendance,
    DisciplinaryIncident,
    DisciplinaryMeasure,
    ParentSummons,
)
from apps.discipline.services.disciplinary_file_service import (
    build_student_disciplinary_file,
)
from apps.discipline.services.exceptions import DisciplineError
from apps.finance.models import Payment
from apps.finance.services.situation_service import student_situation
from apps.secretariat.models import AcademicYear, Guardian, Student


class ParentChildModuleThrottle(AnonRateThrottle):
    scope = "parent_child_modules"
    rate = "120/hour"


def _resolve_guardian(request) -> Guardian | None:
    guardian_id = (
        request.query_params.get("guardian_public_id")
        or request.headers.get("X-Guardian-Public-Id")
        or ""
    ).strip()
    if not guardian_id:
        return None
    return Guardian.objects.filter(
        public_id=guardian_id,
        is_active=True,
        is_archived=False,
    ).first()


def _guardian_owns_student(*, guardian: Guardian, student: Student) -> bool:
    return guardian.student_links.filter(
        student=student,
        student__is_archived=False,
    ).exists()


def _active_year() -> AcademicYear | None:
    return (
        AcademicYear.objects.filter(is_active=True, is_closed=False)
        .order_by("-start_date")
        .first()
    )


def _student_display_name(student: Student) -> str:
    prenom = (student.prenom or "").strip()
    nom = (student.nom or "").strip().upper()
    parts = [p for p in (prenom, nom) if p]
    return " ".join(parts) if parts else str(student.matricule)


def _format_money(amount: Decimal, currency: str = "CDF") -> str:
    quantized = Decimal(amount or 0).quantize(Decimal("1"))
    text = f"{quantized:,.0f}".replace(",", " ")
    return f"{text} {currency}"


def _load_student_for_guardian(request, student_public_id: str):
    guardian = _resolve_guardian(request)
    if guardian is None:
        return None, None, envelope(
            success=False,
            message="Session parent invalide.",
            http_status=400,
        )
    student = Student.objects.filter(
        public_id=student_public_id,
        is_archived=False,
    ).first()
    if student is None or not _guardian_owns_student(guardian=guardian, student=student):
        return None, None, envelope(
            success=False,
            message="Élève introuvable pour ce compte parent.",
            http_status=404,
        )
    return guardian, student, None


class ParentChildAttendanceAPIView(APIView):
    """Liste des dates de présence ou d'absence pour un enfant."""

    permission_classes = [AllowAny]
    throttle_classes = [ParentChildModuleThrottle]
    authentication_classes = []

    PRESENT_STATUSES = {
        DailyAttendance.Status.PRESENT,
        DailyAttendance.Status.LATE,
        DailyAttendance.Status.AUTHORIZED_EXIT,
        DailyAttendance.Status.EXEMPTED,
    }
    ABSENT_STATUSES = {
        DailyAttendance.Status.ABSENT,
        DailyAttendance.Status.JUSTIFIED_ABSENCE,
        DailyAttendance.Status.SICK,
        DailyAttendance.Status.TEMP_SENT_HOME,
    }

    def get(self, request, student_public_id):
        _, student, err = _load_student_for_guardian(request, str(student_public_id))
        if err is not None:
            return err

        kind = (request.query_params.get("kind") or "present").strip().lower()
        if kind not in {"present", "absent"}:
            return envelope(
                success=False,
                message="Paramètre kind invalide (present|absent).",
                http_status=400,
            )

        year = _active_year()
        qs = DailyAttendance.objects.filter(student=student).order_by("-date")
        if year is not None:
            qs = qs.filter(academic_year=year)

        statuses = self.PRESENT_STATUSES if kind == "present" else self.ABSENT_STATUSES
        qs = qs.filter(status__in=statuses)[:120]

        jours = [
            {
                "id": str(row.public_id),
                "date": row.date.isoformat(),
                "date_label": row.date.strftime("%d/%m/%Y"),
                "status": row.status,
                "status_label": row.get_status_display(),
                "note": (row.note or "").strip(),
            }
            for row in qs
        ]

        return envelope(
            message="Présences" if kind == "present" else "Absences",
            data={
                "student_id": str(student.public_id),
                "student_name": _student_display_name(student),
                "kind": kind,
                "school_year_label": year.label if year else "",
                "jours": jours,
            },
        )


def _serialize_parent_disciplinary_dossier(dossier, *, request=None) -> dict:
    """Même contenu que le dossier web, sans brouillons internes."""
    student = dossier.student
    enrollment = dossier.enrollment
    school_class = enrollment.school_class
    stats = dossier.attendance_stats or {}

    photo = None
    if student.photo:
        try:
            photo = student.photo.url
            if request is not None:
                photo = request.build_absolute_uri(photo)
        except ValueError:
            photo = None

    incidents = [
        i
        for i in dossier.incidents
        if getattr(i, "status", None) != DisciplinaryIncident.Status.DRAFT
    ]
    # DisciplinaryMeasure n'a pas de statut BROUILLON.
    measures = list(dossier.measures or [])
    summonses = [
        s
        for s in dossier.summonses
        if getattr(s, "status", None) != ParentSummons.Status.DRAFT
    ]

    return {
        "student_id": str(student.public_id),
        "student_name": _student_display_name(student),
        "reference": dossier.reference,
        "school_year_label": dossier.academic_year.label if dossier.academic_year else "",
        "followup_status": dossier.followup_status,
        "followup_status_label": dossier.followup_status_label,
        "photo": photo,
        "identity": {
            "matricule": student.matricule or "",
            "nom": student.nom or "",
            "postnom": student.postnom or "",
            "prenom": student.prenom or "",
            "sexe_label": student.get_sexe_display() if student.sexe else "",
            "date_naissance_label": (
                student.date_naissance.strftime("%d/%m/%Y")
                if student.date_naissance
                else ""
            ),
            "class_name": school_class.name if school_class else "",
            "level_label": str(school_class.level) if school_class and school_class.level_id else "",
            "section_label": (
                str(school_class.section) if school_class and school_class.section_id else ""
            ),
            "option_label": (
                str(school_class.option) if school_class and school_class.option_id else ""
            ),
            "photo": photo,
        },
        "stats": {
            "present": int(stats.get("present") or 0),
            "late": int(stats.get("late") or 0),
            "absent": int(stats.get("absent") or 0),
            "unjustified": int(stats.get("unjustified") or 0),
            "justified": int(stats.get("justified") or 0),
            "late_minutes": int(stats.get("late_minutes") or 0),
            "positive_observations": int(stats.get("positive_observations") or 0),
            "negative_observations": int(stats.get("negative_observations") or 0),
            "open_incidents": int(stats.get("open_incidents") or 0),
            "closed_incidents": int(stats.get("closed_incidents") or 0),
            "total_incidents": int(stats.get("total_incidents") or 0),
            "total_summons": int(stats.get("total_summons") or 0),
            "pending_summons": int(stats.get("pending_summons") or 0),
            "active_measures": int(stats.get("active_measures") or 0),
        },
        "recent_attendance": [
            {
                "id": str(row.public_id),
                "date": row.date.isoformat() if row.date else "",
                "date_label": row.date.strftime("%d/%m/%Y") if row.date else "",
                "status": row.status,
                "status_label": row.get_status_display(),
                "arrival_time_label": (
                    row.arrival_time.strftime("%H:%M") if row.arrival_time else ""
                ),
                "late_minutes": int(row.late_minutes or 0),
            }
            for row in (dossier.recent_attendance or [])
        ],
        "incidents": [
            {
                "id": str(i.public_id),
                "title": i.title,
                "date": i.incident_date.isoformat() if i.incident_date else "",
                "date_label": (
                    i.incident_date.strftime("%d/%m/%Y") if i.incident_date else ""
                ),
                "category": i.category.name if i.category_id else "",
                "severity": i.severity,
                "severity_label": i.get_severity_display(),
                "status": i.status,
                "status_label": i.get_status_display(),
                "description": (i.description or "").strip()[:400],
            }
            for i in incidents
        ],
        "measures": [
            {
                "id": str(m.public_id),
                "title": (
                    m.measure_type.name
                    if m.measure_type_id
                    else (m.description or "Mesure")
                ),
                "label": (
                    m.measure_type.name
                    if m.measure_type_id
                    else (m.description or "Mesure")
                ),
                "reason": (m.reason or m.description or "").strip()[:280],
                "date_label": (
                    f"{m.start_date.strftime('%d/%m/%Y') if m.start_date else '—'} → "
                    f"{m.end_date.strftime('%d/%m/%Y') if m.end_date else '—'}"
                    if (m.start_date or m.end_date)
                    else ""
                ),
                "status": m.status,
                "status_label": m.get_status_display(),
                "description": (m.reason or m.description or "").strip()[:280],
            }
            for m in measures
        ],
        "summonses": [
            {
                "id": str(s.public_id),
                "title": s.summon_number or "Convocation",
                "label": s.summon_number or "Convocation",
                "date": s.summon_date.isoformat() if s.summon_date else "",
                "date_label": (
                    s.summon_date.strftime("%d/%m/%Y") if s.summon_date else ""
                ),
                "reason": (s.reason or "").strip()[:280],
                "status": s.status,
                "status_label": s.get_status_display(),
                "description": (s.reason or "").strip()[:280],
            }
            for s in summonses
        ],
    }


class ParentChildDisciplineAPIView(APIView):
    """Dossier disciplinaire parent = même builder que le web ERP."""

    permission_classes = [AllowAny]
    throttle_classes = [ParentChildModuleThrottle]
    authentication_classes = []

    def get(self, request, student_public_id):
        _, student, err = _load_student_for_guardian(request, str(student_public_id))
        if err is not None:
            return err

        year = _active_year()
        if year is None:
            return envelope(
                success=False,
                message="Aucune année scolaire active.",
                http_status=404,
            )

        try:
            dossier = build_student_disciplinary_file(
                academic_year=year,
                student_public_id=student.public_id,
            )

            # Mobile : historique plus large que la fiche papier (3 lignes), sans brouillons.
            dossier.incidents = list(
                DisciplinaryIncident.objects.filter(
                    academic_year=year,
                    student=student,
                )
                .exclude(status=DisciplinaryIncident.Status.DRAFT)
                .select_related("category")
                .order_by("-incident_date", "-created_at")[:50]
            )
            dossier.measures = list(
                DisciplinaryMeasure.objects.filter(
                    incident__academic_year=year,
                    student=student,
                )
                .select_related("measure_type", "incident")
                .order_by("-created_at")[:50]
            )
            dossier.summonses = list(
                ParentSummons.objects.filter(
                    academic_year=year,
                    student=student,
                )
                .exclude(status=ParentSummons.Status.DRAFT)
                .order_by("-summon_date", "-created_at")[:50]
            )

            return envelope(
                message="Dossier disciplinaire.",
                data=_serialize_parent_disciplinary_dossier(dossier, request=request),
            )
        except DisciplineError as exc:
            return envelope(
                success=False,
                message=str(exc) or "Dossier disciplinaire indisponible.",
                http_status=404,
            )
        except Exception as exc:  # noqa: BLE001 — surface erreur API parents
            return envelope(
                success=False,
                message=f"Erreur dossier disciplinaire: {exc}",
                http_status=500,
            )


class ParentChildFinanceAPIView(APIView):
    """Situation financière de l'élève (comme la fiche web / QR)."""

    permission_classes = [AllowAny]
    throttle_classes = [ParentChildModuleThrottle]
    authentication_classes = []

    def get(self, request, student_public_id):
        _, student, err = _load_student_for_guardian(request, str(student_public_id))
        if err is not None:
            return err

        year = _active_year()
        if year is None:
            return envelope(
                message="Situation financière.",
                data={
                    "student_id": str(student.public_id),
                    "student_name": _student_display_name(student),
                    "school_year_label": "",
                    "totals": {
                        "amount_due_label": "0 CDF",
                        "amount_paid_label": "0 CDF",
                        "amount_remaining_label": "0 CDF",
                        "tone": "paid",
                    },
                    "obligations": [],
                    "payments": [],
                },
            )

        situation = student_situation(student=student, academic_year=year)
        totals = situation["totals"]
        currency = "CDF"

        obligations = []
        for row in situation["obligations"]:
            fee = row["fee"]
            obligations.append(
                {
                    "id": str(row["obligation"].public_id),
                    "label": fee.label,
                    "amount_due_label": _format_money(row["amount_due"], currency),
                    "amount_paid_label": _format_money(row["amount_paid"], currency),
                    "amount_remaining_label": _format_money(
                        row["amount_remaining"], currency
                    ),
                    "status": row["status"],
                    "tone": row["tone"],
                }
            )

        payments = []
        for payment in situation["payments"][:40]:
            if not isinstance(payment, Payment):
                continue
            payments.append(
                {
                    "id": str(payment.public_id),
                    "receipt_number": payment.receipt_number,
                    "date": payment.payment_date.isoformat(),
                    "date_label": payment.payment_date.strftime("%d/%m/%Y"),
                    "amount_label": _format_money(
                        Decimal(payment.amount_total),
                        payment.currency or currency,
                    ),
                    "status": payment.status,
                    "status_label": payment.get_status_display(),
                }
            )

        return envelope(
            message="Situation financière.",
            data={
                "student_id": str(student.public_id),
                "student_name": _student_display_name(student),
                "school_year_label": year.label,
                "totals": {
                    "amount_due_label": _format_money(totals["amount_due"], currency),
                    "amount_paid_label": _format_money(totals["amount_paid"], currency),
                    "amount_remaining_label": _format_money(
                        totals["amount_remaining"], currency
                    ),
                    "tone": totals["tone"],
                },
                "obligations": obligations,
                "payments": payments,
            },
        )
