"""Parents mobile API — inbox Notifications (finance + secrétariat + discipline)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.api.models import ParentAttendanceNoticeRead, ParentNotificationRead
from apps.api.views import envelope
from apps.discipline.models import (
    ClassAttendanceSheet,
    AbsenceJustification,
    DailyAttendance,
    DisciplinaryIncident,
    DisciplinaryMeasure,
    ExitAuthorization,
    IncidentParticipant,
    ParentSummons,
)
from apps.discipline.services.parent_notification_policy import (
    ATTENDANCE_PARENT_STATUSES,
    EXIT_PARENT_STATUSES,
    INCIDENT_PARENT_STATUSES,
    JUSTIFICATION_PARENT_STATUSES,
    MEASURE_PARENT_STATUSES,
    SOURCE_BY_KIND,
    SUMMONS_PARENT_STATUSES,
)
from apps.finance.models import Payment
from apps.secretariat.models import (
    AcademicYear,
    Communication,
    CommunicationReceipt,
    Guardian,
    Student,
)

ZERO = Decimal("0.00")


class ParentNotificationsThrottle(AnonRateThrottle):
    scope = "parent_notifications"
    rate = "1200/hour"


def _student_display_name(student: Student) -> str:
    prenom = (student.prenom or "").strip()
    nom = (student.nom or "").strip().upper()
    parts = [p for p in (prenom, nom) if p]
    return " ".join(parts) if parts else str(student.matricule)


def _active_academic_year() -> AcademicYear | None:
    return (
        AcademicYear.objects.filter(is_active=True, is_closed=False)
        .order_by("-start_date")
        .first()
    )


def _guardian_students(guardian: Guardian) -> list[Student]:
    students: list[Student] = []
    for link in guardian.student_links.select_related("student"):
        student = link.student
        if student.is_archived:
            continue
        students.append(student)
    return students


def _format_money(amount: Decimal, currency: str = "CDF") -> str:
    quantized = Decimal(amount or ZERO).quantize(Decimal("1"))
    text = f"{quantized:,.0f}".replace(",", " ")
    return f"{text} {currency}"


def _as_aware_dt(value: date | datetime | None) -> datetime:
    """Normalise date/datetime → datetime aware (pour tri chronologique)."""
    if value is None:
        return timezone.make_aware(datetime(1970, 1, 1), timezone.get_current_timezone())
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            return value
        return timezone.make_aware(value, timezone.get_current_timezone())
    # date seule → midi (jamais 23:59 : ça cassait le tri par heure réelle)
    dt = datetime.combine(value, time(12, 0, 0))
    return timezone.make_aware(dt, timezone.get_current_timezone())


def _relative_day_label(value: date | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        local = timezone.localtime(value) if timezone.is_aware(value) else value
        day = local.date()
        clock = local.strftime("%H:%M")
    else:
        day = value
        clock = ""
    today = timezone.localdate()
    delta = (today - day).days
    if delta <= 0:
        return f"Aujourd'hui, {clock}" if clock else "Aujourd'hui"
    if delta == 1:
        return f"Hier, {clock}" if clock else "Hier"
    if clock:
        return f"{day.strftime('%d/%m/%Y')} {clock}"
    return day.strftime("%d/%m/%Y")


def _was_updated(created_at, updated_at) -> bool:
    """True si l'enregistrement a été modifié après sa création."""
    if not created_at or not updated_at:
        return False
    c = _as_aware_dt(created_at)
    u = _as_aware_dt(updated_at)
    return (u - c).total_seconds() > 2


def _activity_moment(*, created_at=None, updated_at=None, published_at=None) -> datetime:
    """
    Tri inbox :
    - nouveau → date/heure de création (ou publication)
    - modifié → date/heure de modification (remonte en tête)
    Ne pas mélanger avec des dates métier seules (jour de paiement, etc.).
    """
    base = published_at or created_at
    if _was_updated(created_at or published_at, updated_at):
        return _as_aware_dt(updated_at)
    if base is not None:
        return _as_aware_dt(base)
    if updated_at is not None:
        return _as_aware_dt(updated_at)
    return _as_aware_dt(None)


def _sort_key(item: dict):
    return _as_aware_dt(item.get("_sort"))


def _iso_occurred(value: date | datetime | None) -> str:
    """ISO en heure locale école (Likasi) pour affichage téléphone cohérent."""
    return timezone.localtime(_as_aware_dt(value)).isoformat()


def _attendance_sort_dt(attendance: DailyAttendance) -> datetime:
    created = getattr(attendance, "created_at", None)
    updated = getattr(attendance, "updated_at", None)
    if _was_updated(created, updated):
        return _as_aware_dt(updated)
    clock = attendance.arrival_time or time.min
    naive = datetime.combine(attendance.date, clock)
    return timezone.make_aware(naive, timezone.get_current_timezone())


def build_parent_notifications(*, guardian: Guardian, limit: int = 40) -> dict:
    """Agrège paiements, messages, convocations, incidents et présences."""
    students = _guardian_students(guardian)
    student_ids = [s.pk for s in students]
    year = _active_academic_year()
    items: list[dict] = []
    discipline_reads = {
        (row.source, row.source_id): row.read_at
        for row in ParentNotificationRead.objects.filter(guardian=guardian)
    }

    def is_discipline_read(source: str, row) -> bool:
        read_at = discipline_reads.get((source, str(row.public_id)))
        if read_at is None:
            return False
        changed_at = getattr(row, "updated_at", None) or getattr(
            row, "created_at", None
        )
        return changed_at is None or _as_aware_dt(read_at) >= _as_aware_dt(changed_at)

    if student_ids:
        pay_qs = Payment.objects.filter(
            student_id__in=student_ids,
            status=Payment.Status.VALID,
        ).select_related("student")
        if year is not None:
            pay_qs = pay_qs.filter(academic_year=year)
        for payment in pay_qs.order_by("-updated_at", "-created_at", "-payment_date")[:limit]:
            student_name = _student_display_name(payment.student)
            amount = _format_money(
                Decimal(payment.amount_total),
                payment.currency or "CDF",
            )
            sort_dt = _activity_moment(
                created_at=payment.created_at,
                updated_at=getattr(payment, "updated_at", None),
            )
            title = (
                "Paiement mis à jour"
                if _was_updated(payment.created_at, getattr(payment, "updated_at", None))
                else "Paiement enregistré"
            )
            items.append(
                {
                    "id": f"payment:{payment.public_id}",
                    "source": "finance_payment",
                    "source_id": str(payment.public_id),
                    "type": "fees",
                    "title": title,
                    "subtitle": f"{student_name} — {amount}",
                    "body": payment.receipt_number or "",
                    "timestamp_label": _relative_day_label(sort_dt),
                    "occurred_at": _iso_occurred(sort_dt),
                    "is_read": not _was_updated(
                        payment.created_at, getattr(payment, "updated_at", None)
                    ),
                    "student_id": str(payment.student.public_id),
                    "student_name": student_name,
                    "_sort": sort_dt,
                }
            )

    today = timezone.localdate()
    receipts = (
        CommunicationReceipt.objects.filter(guardian=guardian)
        .select_related("communication", "student")
        .filter(communication__status=Communication.Status.PUBLISHED)
        .filter(
            Q(communication__expires_at__isnull=True)
            | Q(communication__expires_at__gte=today)
        )
        .order_by("-communication__updated_at", "-communication__published_at", "-created_at")[:limit]
    )
    for receipt in receipts:
        comm = receipt.communication
        student_name = (
            _student_display_name(receipt.student) if receipt.student_id else ""
        )
        published = comm.published_at or receipt.created_at
        category = comm.get_category_display() if comm.category else "Message"
        priority = comm.get_priority_display() if comm.priority else ""
        subtitle_parts = [p for p in (category, priority, student_name) if p]
        sort_dt = _activity_moment(
            created_at=comm.created_at or receipt.created_at,
            updated_at=getattr(comm, "updated_at", None),
            published_at=published,
        )
        updated = _was_updated(
            comm.created_at or published,
            getattr(comm, "updated_at", None),
        )
        title = comm.title or "Message du secrétariat"
        if updated and title and not title.lower().startswith("mise à jour"):
            title = f"Mise à jour — {title}"
        # Relu si modifié après lecture (ou jamais lu).
        is_read = receipt.read_at is not None and not (
            updated
            and receipt.read_at is not None
            and _as_aware_dt(getattr(comm, "updated_at", None))
            > _as_aware_dt(receipt.read_at)
        )
        items.append(
            {
                "id": f"communication:{comm.public_id}",
                "source": "secretariat_communication",
                "source_id": str(comm.public_id),
                "type": "bulletin" if (comm.category or "") == "ACADEMIQUE" else "info",
                "title": title,
                "subtitle": " · ".join(subtitle_parts) if subtitle_parts else "Secrétariat",
                "body": (comm.content or "").strip()[:280],
                "timestamp_label": _relative_day_label(sort_dt),
                "occurred_at": _iso_occurred(sort_dt),
                "is_read": is_read,
                "student_id": str(receipt.student.public_id) if receipt.student_id else "",
                "student_name": student_name,
                "_sort": sort_dt,
            }
        )

    if student_ids:
        summons_qs = (
            ParentSummons.objects.filter(
                student_id__in=student_ids,
                status__in=SUMMONS_PARENT_STATUSES,
            )
            .filter(
                Q(target_guardians=guardian)
                | Q(target_guardians__isnull=True)
            )
            .distinct()
            .select_related("student")
            .order_by("-updated_at", "-summon_date", "-created_at")[:limit]
        )
        for summons in summons_qs:
            student_name = _student_display_name(summons.student)
            sort_dt = _activity_moment(
                created_at=summons.created_at,
                updated_at=getattr(summons, "updated_at", None),
            )
            updated = _was_updated(summons.created_at, getattr(summons, "updated_at", None))
            title = "Convocation mise à jour" if updated else "Convocation"
            items.append(
                {
                    "id": f"summons:{summons.public_id}",
                    "source": "discipline_summons",
                    "source_id": str(summons.public_id),
                    "type": "meeting",
                    "title": title,
                    "subtitle": (
                        f"{student_name} — {summons.reason}"
                        if summons.reason
                        else student_name
                    ),
                    "body": (summons.description or summons.reason or "").strip()[:280],
                    "timestamp_label": _relative_day_label(sort_dt),
                    "occurred_at": _iso_occurred(sort_dt),
                    "is_read": is_discipline_read(
                        SOURCE_BY_KIND["summons"], summons
                    ),
                    "student_id": str(summons.student.public_id),
                    "student_name": student_name,
                    "_sort": sort_dt,
                }
            )

        incidents_qs = (
            DisciplinaryIncident.objects.filter(
                Q(student_id__in=student_ids)
                | Q(participants__student_id__in=student_ids),
                status__in=INCIDENT_PARENT_STATUSES,
            )
            .select_related("student", "category")
            .prefetch_related("participants__student")
            .distinct()
            .order_by("-updated_at", "-incident_date", "-created_at")[:limit]
        )
        for incident in incidents_qs:
            related_students = []
            if incident.student_id in student_ids:
                related_students.append((incident.student, "Élève concerné"))
            related_students.extend(
                (participant.student, participant.get_role_display())
                for participant in incident.participants.all()
                if participant.student_id in student_ids
                and participant.student_id != incident.student_id
            )
            status_label = incident.get_status_display() if incident.status else ""
            sort_dt = _activity_moment(
                created_at=incident.created_at,
                updated_at=getattr(incident, "updated_at", None),
            )
            updated = _was_updated(incident.created_at, getattr(incident, "updated_at", None))
            title = (
                "Incident disciplinaire mis à jour"
                if updated
                else "Incident disciplinaire"
            )
            for student, role_label in related_students:
                student_name = _student_display_name(student)
                items.append(
                    {
                        "id": f"incident:{incident.public_id}:{student.public_id}",
                        "source": SOURCE_BY_KIND["incident"],
                        "source_id": str(incident.public_id),
                        "type": "info",
                        "title": title,
                        "subtitle": " · ".join(
                            (student_name, role_label, status_label)
                        ),
                        "body": (
                            f"{student_name} est lié(e) à cet incident comme "
                            f"« {role_label} ». Consultez le détail."
                        ),
                        "timestamp_label": _relative_day_label(sort_dt),
                        "occurred_at": _iso_occurred(sort_dt),
                        "is_read": is_discipline_read(
                            SOURCE_BY_KIND["incident"], incident
                        ),
                        "student_id": str(student.public_id),
                        "student_name": student_name,
                        "role": role_label,
                        "_sort": sort_dt,
                    }
                )

        measures = (
            DisciplinaryMeasure.objects.filter(
                student_id__in=student_ids,
                status__in=MEASURE_PARENT_STATUSES,
            )
            .select_related("student", "measure_type")
            .order_by("-updated_at", "-created_at")[:limit]
        )
        for measure in measures:
            student_name = _student_display_name(measure.student)
            sort_dt = _activity_moment(
                created_at=measure.created_at, updated_at=measure.updated_at
            )
            updated = _was_updated(measure.created_at, measure.updated_at)
            items.append(
                {
                    "id": f"measure:{measure.public_id}",
                    "source": SOURCE_BY_KIND["measure"],
                    "source_id": str(measure.public_id),
                    "type": "info",
                    "title": (
                        "Mesure disciplinaire mise à jour"
                        if updated
                        else "Mesure disciplinaire"
                    ),
                    "subtitle": (
                        f"{student_name} · {measure.measure_type.name} · "
                        f"{measure.get_status_display()}"
                    ),
                    "body": (measure.description or measure.reason or "").strip()[:280],
                    "timestamp_label": _relative_day_label(sort_dt),
                    "occurred_at": _iso_occurred(sort_dt),
                    "is_read": is_discipline_read(
                        SOURCE_BY_KIND["measure"], measure
                    ),
                    "student_id": str(measure.student.public_id),
                    "student_name": student_name,
                    "_sort": sort_dt,
                }
            )

        exits = (
            ExitAuthorization.objects.filter(
                student_id__in=student_ids,
                status__in=EXIT_PARENT_STATUSES,
            )
            .select_related("student")
            .order_by("-updated_at", "-date", "-created_at")[:limit]
        )
        for exit_row in exits:
            student_name = _student_display_name(exit_row.student)
            sort_dt = _activity_moment(
                created_at=exit_row.created_at, updated_at=exit_row.updated_at
            )
            items.append(
                {
                    "id": f"exit:{exit_row.public_id}",
                    "source": SOURCE_BY_KIND["exit"],
                    "source_id": str(exit_row.public_id),
                    "type": "info",
                    "title": "Autorisation de sortie",
                    "subtitle": (
                        f"{student_name} · {exit_row.get_status_display()}"
                    ),
                    "body": (exit_row.reason or "").strip()[:280],
                    "timestamp_label": _relative_day_label(sort_dt),
                    "occurred_at": _iso_occurred(sort_dt),
                    "is_read": is_discipline_read(
                        SOURCE_BY_KIND["exit"], exit_row
                    ),
                    "student_id": str(exit_row.student.public_id),
                    "student_name": student_name,
                    "_sort": sort_dt,
                }
            )

        justifications = (
            AbsenceJustification.objects.filter(
                attendance__student_id__in=student_ids,
                status__in=JUSTIFICATION_PARENT_STATUSES,
            )
            .select_related("attendance", "attendance__student")
            .order_by("-updated_at", "-submitted_at")[:limit]
        )
        for justification in justifications:
            student = justification.attendance.student
            student_name = _student_display_name(student)
            sort_dt = _activity_moment(
                created_at=justification.created_at,
                updated_at=justification.updated_at,
            )
            items.append(
                {
                    "id": f"justification:{justification.public_id}",
                    "source": SOURCE_BY_KIND["justification"],
                    "source_id": str(justification.public_id),
                    "type": "info",
                    "title": "Justification d’absence",
                    "subtitle": (
                        f"{student_name} · {justification.get_status_display()}"
                    ),
                    "body": (
                        justification.review_note
                        or justification.reason
                        or ""
                    ).strip()[:280],
                    "timestamp_label": _relative_day_label(sort_dt),
                    "occurred_at": _iso_occurred(sort_dt),
                    "is_read": is_discipline_read(
                        SOURCE_BY_KIND["justification"], justification
                    ),
                    "student_id": str(student.public_id),
                    "student_name": student_name,
                    "_sort": sort_dt,
                }
            )

        att_qs = DailyAttendance.objects.filter(
            student_id__in=student_ids,
            status__in=ATTENDANCE_PARENT_STATUSES,
            date__gte=today - timedelta(days=30),
        ).select_related("student", "enrollment", "enrollment__school_class")
        if year is not None:
            att_qs = att_qs.filter(academic_year=year)
        # Uniquement si la feuille de classe du jour est validée / clôturée.
        validated_sheet_keys = set(
            ClassAttendanceSheet.objects.filter(
                status__in=[
                    ClassAttendanceSheet.Status.VALIDATED,
                    ClassAttendanceSheet.Status.CLOSED,
                ],
                date__gte=today - timedelta(days=30),
            ).values_list("school_class_id", "date")
        )
        attendances = [
            a
            for a in att_qs.order_by("-date", "-updated_at")[: limit * 3]
            if (
                getattr(a, "enrollment_id", None)
                and (a.enrollment.school_class_id, a.date) in validated_sheet_keys
            )
        ][:limit]
        legacy_attendance_reads = dict(
            ParentAttendanceNoticeRead.objects.filter(
                guardian=guardian,
                attendance_id__in=[a.pk for a in attendances],
            ).values_list("attendance_id", "read_at")
        )
        # Historique ancien = déjà « vu » (évite un badge explosif au déploiement).
        unread_from = today - timedelta(days=1)
        for attendance in attendances:
            student_name = _student_display_name(attendance.student)
            time_label = (
                attendance.arrival_time.strftime("%H:%M")
                if attendance.arrival_time
                else ""
            )
            is_late = attendance.status == DailyAttendance.Status.LATE
            if is_late:
                title = "Retard signalé"
                body = (
                    f"{student_name} est arrivé(e) en retard"
                    + (f" à {time_label}" if time_label else "")
                    + (
                        f" ({attendance.late_minutes} min)."
                        if attendance.late_minutes
                        else "."
                    )
                )
                subtitle = (
                    f"{student_name} — Retard"
                    + (f" {attendance.late_minutes} min" if attendance.late_minutes else "")
                )
            elif attendance.status == DailyAttendance.Status.PRESENT:
                title = "Présence confirmée"
                body = (
                    f"{student_name} est bien arrivé(e) à l’école"
                    + (f" à {time_label}." if time_label else ".")
                )
                subtitle = (
                    f"{student_name} — Présent"
                    + (f" à {time_label}" if time_label else "")
                )
            else:
                status_label = attendance.get_status_display()
                title = status_label
                body = (
                    f"Le statut de présence de {student_name} est "
                    f"« {status_label} »."
                )
                subtitle = f"{student_name} — {status_label}"
            legacy_read_at = legacy_attendance_reads.get(attendance.pk)
            legacy_is_current = bool(legacy_read_at) and _as_aware_dt(
                legacy_read_at
            ) >= _as_aware_dt(attendance.updated_at)
            is_read = (
                is_discipline_read(SOURCE_BY_KIND["attendance"], attendance)
                or legacy_is_current
                or attendance.date < unread_from
            )
            sort_dt = _attendance_sort_dt(attendance)
            items.append(
                {
                    "id": f"attendance:{attendance.public_id}",
                    "source": "discipline_attendance",
                    "source_id": str(attendance.public_id),
                    "type": "info",
                    "title": title,
                    "subtitle": subtitle,
                    "body": body,
                    "timestamp_label": _relative_day_label(sort_dt),
                    "occurred_at": _iso_occurred(sort_dt),
                    "is_read": is_read,
                    "student_id": str(attendance.student.public_id),
                    "student_name": student_name,
                    "_sort": sort_dt,
                }
            )

    # Plus récent en premier (jamais par titre / type).
    items.sort(key=_sort_key, reverse=True)
    truncated = items[:limit]
    unread = sum(1 for it in truncated if not it.get("is_read"))
    for it in truncated:
        it.pop("_sort", None)

    return {
        "unread_count": unread,
        "total_count": len(truncated),
        "items": truncated,
    }


class ParentNotificationsAPIView(APIView):
    """Liste unifiée des notifications parent + marquage lu (POST)."""

    permission_classes = [AllowAny]
    throttle_classes = [ParentNotificationsThrottle]
    authentication_classes = []

    def _resolve_guardian(self, request):
        guardian_id = (
            request.query_params.get("guardian_public_id")
            or request.data.get("guardian_public_id")
            or request.headers.get("X-Guardian-Public-Id")
            or ""
        ).strip()
        if not guardian_id:
            return None, envelope(
                success=False,
                message="Session parent invalide.",
                http_status=400,
            )
        guardian = Guardian.objects.filter(
            public_id=guardian_id,
            is_active=True,
            is_archived=False,
        ).first()
        if guardian is None:
            return None, envelope(
                success=False,
                message="Compte parent introuvable.",
                http_status=404,
            )
        return guardian, None

    def get(self, request):
        guardian, err = self._resolve_guardian(request)
        if err is not None:
            return err

        try:
            limit = int(request.query_params.get("limit") or 40)
        except (TypeError, ValueError):
            limit = 40
        limit = max(1, min(limit, 80))

        data = build_parent_notifications(guardian=guardian, limit=limit)
        return envelope(message="Notifications.", data=data)

    def post(self, request):
        """Marque l'inbox comme lue (badge → 0 jusqu'à de nouvelles notifs)."""
        guardian, err = self._resolve_guardian(request)
        if err is not None:
            return err

        data = mark_parent_notifications_read(guardian=guardian)
        return envelope(
            message="Notifications marquées comme lues.",
            data=data,
        )


def mark_parent_notifications_read(*, guardian: Guardian, limit: int = 40) -> dict:
    """Persiste la lecture côté serveur (survit aux redémarrages app)."""
    now = timezone.now()
    students = _guardian_students(guardian)
    student_ids = [s.pk for s in students]
    year = _active_academic_year()

    CommunicationReceipt.objects.filter(
        guardian=guardian,
        read_at__isnull=True,
    ).update(read_at=now)

    if student_ids:
        att_qs = DailyAttendance.objects.filter(
            student_id__in=student_ids,
            status__in=ATTENDANCE_PARENT_STATUSES,
            date__gte=timezone.localdate() - timedelta(days=30),
        )
        if year is not None:
            att_qs = att_qs.filter(academic_year=year)
        already = set(
            ParentAttendanceNoticeRead.objects.filter(
                guardian=guardian,
                attendance_id__in=att_qs.values_list("pk", flat=True),
            ).values_list("attendance_id", flat=True)
        )
        to_create = [
            ParentAttendanceNoticeRead(guardian=guardian, attendance_id=pk)
            for pk in att_qs.values_list("pk", flat=True)
            if pk not in already
        ]
        if to_create:
            ParentAttendanceNoticeRead.objects.bulk_create(
                to_create,
                ignore_conflicts=True,
            )

        receipt_keys: set[tuple[str, str]] = set()
        for public_id in ParentSummons.objects.filter(
            student_id__in=student_ids,
            status__in=SUMMONS_PARENT_STATUSES,
        ).filter(
            Q(target_guardians=guardian)
            | Q(target_guardians__isnull=True)
        ).distinct().values_list("public_id", flat=True):
            receipt_keys.add((SOURCE_BY_KIND["summons"], str(public_id)))
        for public_id in DisciplinaryIncident.objects.filter(
            Q(student_id__in=student_ids)
            | Q(participants__student_id__in=student_ids),
            status__in=INCIDENT_PARENT_STATUSES,
        ).values_list("public_id", flat=True):
            receipt_keys.add((SOURCE_BY_KIND["incident"], str(public_id)))
        for public_id in DisciplinaryMeasure.objects.filter(
            student_id__in=student_ids,
            status__in=MEASURE_PARENT_STATUSES,
        ).values_list("public_id", flat=True):
            receipt_keys.add((SOURCE_BY_KIND["measure"], str(public_id)))
        for public_id in ExitAuthorization.objects.filter(
            student_id__in=student_ids,
            status__in=EXIT_PARENT_STATUSES,
        ).values_list("public_id", flat=True):
            receipt_keys.add((SOURCE_BY_KIND["exit"], str(public_id)))
        for public_id in AbsenceJustification.objects.filter(
            attendance__student_id__in=student_ids,
            status__in=JUSTIFICATION_PARENT_STATUSES,
        ).values_list("public_id", flat=True):
            receipt_keys.add((SOURCE_BY_KIND["justification"], str(public_id)))
        for public_id in att_qs.values_list("public_id", flat=True):
            receipt_keys.add((SOURCE_BY_KIND["attendance"], str(public_id)))

        existing_keys = set(
            ParentNotificationRead.objects.filter(guardian=guardian).values_list(
                "source", "source_id"
            )
        )
        ParentNotificationRead.objects.filter(guardian=guardian).update(read_at=now)
        ParentNotificationRead.objects.bulk_create(
            [
                ParentNotificationRead(
                    guardian=guardian,
                    source=source,
                    source_id=source_id,
                    read_at=now,
                )
                for source, source_id in receipt_keys - existing_keys
            ],
            ignore_conflicts=True,
        )

    return build_parent_notifications(guardian=guardian, limit=limit)
