"""Parents mobile API — Accueil (overview + activités récentes)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.api.parents_notifications import build_parent_notifications
from apps.api.views import envelope
from apps.finance.models import Payment, StudentFeeObligation
from apps.secretariat.models import AcademicYear, Guardian, Student

ZERO = Decimal("0.00")
MONEY = DecimalField(max_digits=14, decimal_places=2)


class ParentHomeThrottle(AnonRateThrottle):
    scope = "parent_home"
    rate = "1200/hour"


def _guardian_display_name(guardian: Guardian) -> str:
    return " ".join(
        part for part in (guardian.prenom, guardian.nom) if part
    ).strip() or str(guardian)


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


def _school_year_label(year: AcademicYear | None) -> str:
    if year is None:
        return "Année scolaire"
    label = (year.label or "").strip()
    if not label:
        return "Année scolaire"
    if label.lower().startswith("année"):
        return label
    return f"Année scolaire {label}"


def _guardian_student_ids(guardian: Guardian) -> list[int]:
    links = guardian.student_links.select_related("student")
    ids: list[int] = []
    for link in links:
        student = link.student
        if student.is_archived:
            continue
        ids.append(student.pk)
    return ids


def _format_money(amount: Decimal, currency: str = "CDF") -> str:
    quantized = amount.quantize(Decimal("1"))
    text = f"{quantized:,.0f}".replace(",", " ")
    return f"{text} {currency}"


def _unpaid_balance_label(*, student_ids: list[int], year: AcademicYear | None) -> str:
    if not student_ids or year is None:
        return "Aucun"
    remaining = (
        StudentFeeObligation.objects.filter(
            student_id__in=student_ids,
            fee__academic_year=year,
            status__in=[
                StudentFeeObligation.Status.UNPAID,
                StudentFeeObligation.Status.PARTIAL,
            ],
        )
        .exclude(status=StudentFeeObligation.Status.CANCELLED)
        .aggregate(
            total=Coalesce(
                Sum(F("amount_due") - F("amount_paid")),
                Value(ZERO, output_field=MONEY),
                output_field=MONEY,
            )
        )["total"]
    )
    remaining = Decimal(remaining or ZERO)
    if remaining <= 0:
        return "Aucun"
    return _format_money(remaining)


def _paid_balance_label(*, student_ids: list[int], year: AcademicYear | None) -> str:
    """Cumul des montants déjà payés (tous les enfants du responsable)."""
    if not student_ids or year is None:
        return "Aucun"
    paid = (
        Payment.objects.filter(
            student_id__in=student_ids,
            academic_year=year,
            status=Payment.Status.VALID,
        ).aggregate(
            total=Coalesce(
                Sum("amount_total"),
                Value(ZERO, output_field=MONEY),
                output_field=MONEY,
            )
        )["total"]
    )
    paid = Decimal(paid or ZERO)
    if paid <= 0:
        return "Aucun"
    return _format_money(paid)


def _relative_day_label(value: date | datetime) -> str:
    if isinstance(value, datetime):
        day = timezone.localtime(value).date() if timezone.is_aware(value) else value.date()
    else:
        day = value
    today = timezone.localdate()
    delta = (today - day).days
    if delta <= 0:
        return "Aujourd'hui"
    if delta == 1:
        return "Hier"
    return day.strftime("%d/%m/%Y")


def _recent_payment_activities(
    *,
    student_ids: list[int],
    year: AcademicYear | None,
    limit: int = 8,
) -> list[dict]:
    if not student_ids:
        return []
    qs = Payment.objects.filter(
        student_id__in=student_ids,
        status=Payment.Status.VALID,
    ).select_related("student")
    if year is not None:
        qs = qs.filter(academic_year=year)
    qs = qs.order_by("-payment_date", "-created_at")[:limit]

    activities: list[dict] = []
    for payment in qs:
        student_name = _student_display_name(payment.student)
        amount = _format_money(Decimal(payment.amount_total), payment.currency or "CDF")
        activities.append(
            {
                "id": str(payment.public_id),
                "title": "Paiement enregistré",
                "subtitle": f"{student_name} — {amount}",
                "timestamp_label": _relative_day_label(payment.payment_date),
                "type": "fees",
            }
        )
    return activities


def build_parent_home_overview(*, guardian: Guardian) -> dict:
    year = _active_academic_year()
    student_ids = _guardian_student_ids(guardian)
    children_count = len(student_ids)
    notifications = build_parent_notifications(guardian=guardian, limit=40)
    sorted_items = list(notifications.get("items") or [])
    # Même ordre que l'onglet « Toutes » (déjà trié côté build, on sécurise).
    sorted_items.sort(key=lambda it: it.get("occurred_at") or "", reverse=True)
    activities = [
        {
            "id": item["id"],
            "title": item["title"],
            "subtitle": item["subtitle"],
            "body": item.get("body") or item.get("subtitle") or "",
            "timestamp_label": item["timestamp_label"],
            "occurred_at": item.get("occurred_at") or "",
            "type": item["type"],
            "source": item.get("source") or "",
            "source_id": item.get("source_id") or "",
        }
        for item in sorted_items[:3]
    ]

    return {
        "display_name": _guardian_display_name(guardian),
        "guardian_public_id": str(guardian.public_id),
        "school_year_label": _school_year_label(year),
        "children_count": children_count,
        "notifications_count": int(notifications.get("total_count") or 0),
        "unread_notifications_badge": int(notifications.get("unread_count") or 0),
        # Notes / bulletins parents pas encore exposés.
        "general_average_percent": None,
        "paid_balance_label": _paid_balance_label(
            student_ids=student_ids,
            year=year,
        ),
        "unpaid_balance_label": _unpaid_balance_label(
            student_ids=student_ids,
            year=year,
        ),
        "activities": activities,
    }


class ParentHomeOverviewAPIView(APIView):
    """Tableau de bord Accueil pour un responsable (Guardian).

    Auth provisoire mobile : `guardian_public_id` (query ou header
    `X-Guardian-Public-Id`) jusqu'à l'arrivée du JWT parents.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ParentHomeThrottle]
    authentication_classes = []

    def get(self, request):
        guardian_id = (
            request.query_params.get("guardian_public_id")
            or request.headers.get("X-Guardian-Public-Id")
            or ""
        ).strip()
        if not guardian_id:
            return envelope(
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
            return envelope(
                success=False,
                message="Compte parent introuvable.",
                http_status=404,
            )

        data = build_parent_home_overview(guardian=guardian)
        return envelope(message="Vue d'ensemble Accueil.", data=data)
