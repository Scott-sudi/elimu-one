"""Parents mobile API — détail notifications (communication / reçu paiement)."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from django.http import FileResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.api.parents_child_modules import (
    _format_money,
    _guardian_owns_student,
    _resolve_guardian,
    _student_display_name,
)
from apps.api.models import ParentNotificationRead
from apps.api.views import envelope
from apps.discipline.models import (
    AbsenceJustification,
    ClassAttendanceSheet,
    DailyAttendance,
    DisciplinaryIncident,
    DisciplinaryMeasure,
    ExitAuthorization,
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
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.receipt_service import amount_in_words_fr, build_receipt_pdf
from apps.secretariat.models import Communication, CommunicationReceipt


class ParentNotificationDetailThrottle(AnonRateThrottle):
    scope = "parent_notification_detail"
    rate = "180/hour"


def _mark_discipline_read(*, guardian, kind: str, row) -> None:
    receipt, _ = ParentNotificationRead.objects.get_or_create(
        guardian=guardian,
        source=SOURCE_BY_KIND[kind],
        source_id=str(row.public_id),
    )
    if receipt.read_at < row.updated_at:
        receipt.read_at = timezone.now()
        receipt.save(update_fields=["read_at"])


def _payment_purpose(payment: Payment) -> str:
    parts: list[str] = []
    for alloc in payment.allocations.all():
        obligation = getattr(alloc, "obligation", None)
        fee = getattr(obligation, "fee", None) if obligation is not None else None
        if fee is not None:
            label = (fee.label or fee.code or "").strip()
            if label:
                parts.append(label)
    return " · ".join(parts) if parts else "Frais scolaires"


class ParentCommunicationDetailAPIView(APIView):
    """Détail d'un message secrétariat destiné au parent."""

    permission_classes = [AllowAny]
    throttle_classes = [ParentNotificationDetailThrottle]
    authentication_classes = []

    def get(self, request, public_id):
        guardian = _resolve_guardian(request)
        if guardian is None:
            return envelope(
                success=False,
                message="Session parent invalide.",
                http_status=400,
            )

        receipt = (
            CommunicationReceipt.objects.filter(
                guardian=guardian,
                communication__public_id=public_id,
                communication__status=Communication.Status.PUBLISHED,
            )
            .select_related("communication", "student")
            .order_by("-created_at")
            .first()
        )
        if receipt is None:
            return envelope(
                success=False,
                message="Message introuvable.",
                http_status=404,
            )

        if receipt.read_at is None:
            receipt.read_at = timezone.now()
            receipt.save(update_fields=["read_at"])

        comm = receipt.communication
        attachment_url = ""
        if comm.attachment:
            try:
                attachment_url = request.build_absolute_uri(comm.attachment.url)
            except ValueError:
                attachment_url = ""

        student_name = (
            _student_display_name(receipt.student) if receipt.student_id else ""
        )
        published = comm.published_at or receipt.created_at

        return envelope(
            message="Détail du message.",
            data={
                "id": str(comm.public_id),
                "source": "secretariat_communication",
                "title": comm.title or "Message du secrétariat",
                "content": (comm.content or "").strip(),
                "category": comm.category or "",
                "category_label": comm.get_category_display() if comm.category else "",
                "priority": comm.priority or "",
                "priority_label": comm.get_priority_display() if comm.priority else "",
                "published_at": published.isoformat() if published else "",
                "published_label": (
                    timezone.localtime(published).strftime("%d/%m/%Y %H:%M")
                    if published
                    else ""
                ),
                "student_id": str(receipt.student.public_id) if receipt.student_id else "",
                "student_name": student_name,
                "attachment_url": attachment_url,
                "is_read": True,
            },
        )


class ParentPaymentReceiptAPIView(APIView):
    """Métadonnées du reçu (mêmes infos que le PDF web)."""

    permission_classes = [AllowAny]
    throttle_classes = [ParentNotificationDetailThrottle]
    authentication_classes = []

    def get(self, request, public_id):
        guardian = _resolve_guardian(request)
        if guardian is None:
            return envelope(
                success=False,
                message="Session parent invalide.",
                http_status=400,
            )

        payment = (
            Payment.objects.filter(
                public_id=public_id,
                status=Payment.Status.VALID,
            )
            .select_related(
                "student",
                "enrollment",
                "enrollment__school_class",
                "academic_year",
                "recorded_by",
            )
            .prefetch_related(
                "allocations__obligation__fee",
                "allocations__obligation__fee__category",
            )
            .first()
        )
        if payment is None:
            return envelope(
                success=False,
                message="Reçu introuvable.",
                http_status=404,
            )
        if not _guardian_owns_student(guardian=guardian, student=payment.student):
            return envelope(
                success=False,
                message="Reçu introuvable pour ce compte parent.",
                http_status=404,
            )

        student = payment.student
        enrollment = payment.enrollment
        school_class = enrollment.school_class if enrollment else None
        year = payment.academic_year
        currency = payment.currency or "CDF"
        amount = Decimal(payment.amount_total or 0)

        remaining = Decimal("0.00")
        for allocation in payment.allocations.all():
            obligation = allocation.obligation
            remaining += Decimal(str(obligation.amount_remaining))

        recorder = ""
        if payment.recorded_by_id:
            user = payment.recorded_by
            recorder = (
                getattr(user, "get_full_name", lambda: "")()
                or getattr(user, "username", "")
                or str(user)
            ).strip()

        pdf_url = request.build_absolute_uri(
            f"/api/v1/parents/payments/{payment.public_id}/receipt.pdf"
            f"?guardian_public_id={guardian.public_id}&inline=1"
        )

        return envelope(
            message="Reçu de paiement.",
            data={
                "id": str(payment.public_id),
                "source": "finance_payment",
                "receipt_number": payment.receipt_number or "",
                "payment_date": payment.payment_date.isoformat()
                if payment.payment_date
                else "",
                "payment_date_label": payment.payment_date.strftime("%d/%m/%Y")
                if payment.payment_date
                else "",
                "student_id": str(student.public_id),
                "student_name": _student_display_name(student),
                "matricule": student.matricule or "",
                "class_name": school_class.name if school_class else "",
                "school_year_label": year.label if year else "",
                "amount": str(amount),
                "amount_label": _format_money(amount, currency),
                "amount_in_words": amount_in_words_fr(amount, currency),
                "remaining_label": _format_money(remaining, currency),
                "purpose": _payment_purpose(payment),
                "payment_method": payment.payment_method or "",
                "payment_method_label": payment.get_payment_method_display()
                if payment.payment_method
                else "",
                "currency": currency,
                "recorded_by": recorder,
                "pdf_url": pdf_url,
            },
        )


@method_decorator(xframe_options_exempt, name="dispatch")
class ParentPaymentReceiptPdfAPIView(APIView):
    """PDF du reçu — identique au générateur web (`build_receipt_pdf`)."""

    permission_classes = [AllowAny]
    throttle_classes = [ParentNotificationDetailThrottle]
    authentication_classes = []

    def get(self, request, public_id):
        guardian = _resolve_guardian(request)
        if guardian is None:
            return envelope(
                success=False,
                message="Session parent invalide.",
                http_status=400,
            )

        payment = Payment.objects.filter(
            public_id=public_id,
            status=Payment.Status.VALID,
        ).first()
        if payment is None or not _guardian_owns_student(
            guardian=guardian, student=payment.student
        ):
            return envelope(
                success=False,
                message="Reçu introuvable.",
                http_status=404,
            )

        try:
            content = build_receipt_pdf(
                payment=payment,
                actor=None,
                request=request,
                audit=False,
            )
        except FinanceError as exc:
            return envelope(success=False, message=str(exc), http_status=400)

        inline = request.query_params.get("inline") == "1"
        filename = f"{payment.receipt_number or payment.public_id}.pdf"
        return FileResponse(
            BytesIO(content),
            content_type="application/pdf",
            as_attachment=not inline,
            filename=filename,
        )


class ParentDisciplineDetailAPIView(APIView):
    """Détail convocation ou incident (inbox notifications)."""

    permission_classes = [AllowAny]
    throttle_classes = [ParentNotificationDetailThrottle]
    authentication_classes = []

    def get(self, request, kind, public_id):
        guardian = _resolve_guardian(request)
        if guardian is None:
            return envelope(
                success=False,
                message="Session parent invalide.",
                http_status=400,
            )

        kind = (kind or "").strip().lower()
        if kind == "summons":
            row = (
                ParentSummons.objects.filter(
                    public_id=public_id,
                    status__in=SUMMONS_PARENT_STATUSES,
                )
                .select_related("student")
                .prefetch_related("target_guardians")
                .first()
            )
            targeted = row is not None and row.target_guardians.exists()
            authorized = row is not None and (
                row.target_guardians.filter(pk=guardian.pk).exists()
                if targeted
                else _guardian_owns_student(guardian=guardian, student=row.student)
            )
            if not authorized:
                return envelope(
                    success=False,
                    message="Convocation introuvable.",
                    http_status=404,
                )
            _mark_discipline_read(guardian=guardian, kind="summons", row=row)
            return envelope(
                message="Détail de la convocation.",
                data={
                    "id": str(row.public_id),
                    "source": "discipline_summons",
                    "title": "Convocation",
                    "reason": row.reason or "",
                    "content": (row.description or row.reason or "").strip(),
                    "summon_date_label": row.summon_date.strftime("%d/%m/%Y")
                    if row.summon_date
                    else "",
                    "summon_time_label": row.summon_time.strftime("%H:%M")
                    if row.summon_time
                    else "",
                    "location": row.location or "",
                    "student_name": _student_display_name(row.student),
                    "status_label": row.get_status_display(),
                },
            )

        if kind == "incident":
            row = (
                DisciplinaryIncident.objects.filter(
                    public_id=public_id,
                    status__in=INCIDENT_PARENT_STATUSES,
                )
                .select_related("student", "category")
                .prefetch_related("participants__student")
                .first()
            )
            owned_students = {
                link.student_id
                for link in guardian.student_links.select_related("student")
                if not link.student.is_archived
            }
            participant = None
            if row is not None:
                participant = next(
                    (
                        item
                        for item in row.participants.all()
                        if item.student_id in owned_students
                    ),
                    None,
                )
            owns_main = row is not None and row.student_id in owned_students
            if row is None or (not owns_main and participant is None):
                return envelope(
                    success=False,
                    message="Incident introuvable.",
                    http_status=404,
                )
            related_student = row.student if owns_main else participant.student
            role_label = (
                "Élève concerné" if owns_main else participant.get_role_display()
            )
            _mark_discipline_read(guardian=guardian, kind="incident", row=row)
            return envelope(
                message="Détail de l'incident.",
                data={
                    "id": str(row.public_id),
                    "source": "discipline_incident",
                    "title": "Incident disciplinaire",
                    "content": (
                        f"{_student_display_name(related_student)} est lié(e) à "
                        f"cet incident comme « {role_label} »."
                    ),
                    "severity_label": row.get_severity_display() if row.severity else "",
                    "status_label": row.get_status_display() if row.status else "",
                    "incident_date_label": row.incident_date.strftime("%d/%m/%Y")
                    if row.incident_date
                    else "",
                    "student_name": _student_display_name(related_student),
                    "role_label": role_label,
                    "category_label": row.category.name
                    if getattr(row, "category_id", None)
                    else "",
                },
            )

        model_config = {
            "measure": (
                DisciplinaryMeasure,
                MEASURE_PARENT_STATUSES,
                ("student", "measure_type"),
            ),
            "exit": (
                ExitAuthorization,
                EXIT_PARENT_STATUSES,
                ("student",),
            ),
            "justification": (
                AbsenceJustification,
                JUSTIFICATION_PARENT_STATUSES,
                ("attendance", "attendance__student"),
            ),
            "attendance": (
                DailyAttendance,
                ATTENDANCE_PARENT_STATUSES,
                ("student", "enrollment", "enrollment__school_class"),
            ),
        }
        if kind in model_config:
            model, statuses, related = model_config[kind]
            row = (
                model.objects.filter(public_id=public_id, status__in=statuses)
                .select_related(*related)
                .first()
            )
            student = None
            if row is not None:
                student = (
                    row.attendance.student
                    if kind == "justification"
                    else row.student
                )
            if row is None or not _guardian_owns_student(
                guardian=guardian, student=student
            ):
                return envelope(
                    success=False,
                    message="Notification introuvable.",
                    http_status=404,
                )
            if kind == "attendance":
                sheet_validated = ClassAttendanceSheet.objects.filter(
                    school_class_id=row.enrollment.school_class_id,
                    date=row.date,
                    status__in=[
                        ClassAttendanceSheet.Status.VALIDATED,
                        ClassAttendanceSheet.Status.CLOSED,
                    ],
                ).exists()
                if not sheet_validated:
                    return envelope(
                        success=False,
                        message="Notification introuvable.",
                        http_status=404,
                    )

            _mark_discipline_read(guardian=guardian, kind=kind, row=row)
            data = {
                "id": str(row.public_id),
                "source": SOURCE_BY_KIND[kind],
                "student_id": str(student.public_id),
                "student_name": _student_display_name(student),
                "status": row.status,
                "status_label": row.get_status_display(),
                "is_read": True,
            }
            if kind == "measure":
                data.update(
                    {
                        "title": "Mesure disciplinaire",
                        "measure_type": row.measure_type.name,
                        "content": (row.description or row.reason or "").strip(),
                        "start_date": row.start_date.isoformat()
                        if row.start_date
                        else "",
                        "end_date": row.end_date.isoformat() if row.end_date else "",
                    }
                )
            elif kind == "exit":
                data.update(
                    {
                        "title": "Autorisation de sortie",
                        "content": (row.reason or "").strip(),
                        "date": row.date.isoformat(),
                        "planned_exit_time": row.planned_exit_time.strftime("%H:%M")
                        if row.planned_exit_time
                        else "",
                        "actual_exit_time": row.actual_exit_time.strftime("%H:%M")
                        if row.actual_exit_time
                        else "",
                        "actual_return_time": row.actual_return_time.strftime("%H:%M")
                        if row.actual_return_time
                        else "",
                    }
                )
            elif kind == "justification":
                data.update(
                    {
                        "title": "Justification d’absence",
                        "content": (row.reason or row.description or "").strip(),
                        "review_note": (row.review_note or "").strip(),
                        "attendance_date": row.attendance.date.isoformat(),
                    }
                )
            else:
                data.update(
                    {
                        "title": row.get_status_display(),
                        "content": (row.note or "").strip(),
                        "date": row.date.isoformat(),
                        "arrival_time": row.arrival_time.strftime("%H:%M")
                        if row.arrival_time
                        else "",
                        "late_minutes": row.late_minutes,
                    }
                )
            return envelope(message="Détail de la notification.", data=data)

        return envelope(
            success=False,
            message=(
                "Type invalide "
                "(summons|incident|measure|exit|justification|attendance)."
            ),
            http_status=400,
        )
