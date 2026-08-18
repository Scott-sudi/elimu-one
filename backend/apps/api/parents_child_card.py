"""Parents mobile API — carte d'élève (PNG secrétariat, identique au web)."""

from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.api.parents_child_modules import _load_student_for_guardian
from apps.api.views import envelope
from apps.core.branding import school_display_name, school_display_slogan
from apps.secretariat.models import StudentCard
from apps.secretariat.services import card_service


class ParentChildCardThrottle(AnonRateThrottle):
    scope = "parent_child_card"
    rate = "120/hour"


def _serialize_card(*, card: StudentCard, request) -> dict:
    student = card.student
    enrollment = card.enrollment
    school_class = enrollment.school_class if enrollment else None
    section = ""
    option = ""
    class_name = ""
    year_label = ""
    if school_class is not None:
        class_name = school_class.name or ""
        if getattr(school_class, "section_id", None):
            section = school_class.section.name or ""
        if getattr(school_class, "option_id", None):
            option = school_class.option.name or ""
    if enrollment and enrollment.academic_year_id:
        year_label = enrollment.academic_year.label or str(enrollment.academic_year)

    if not section:
        section = "Tronc commun"
    if not option:
        option = "—"

    card_service.ensure_card_png(card)
    preview = card_service.card_preview_url(card)
    preview_abs = request.build_absolute_uri(preview) if preview else ""

    photo = ""
    if student.photo:
        try:
            photo = request.build_absolute_uri(student.photo.url)
        except ValueError:
            photo = ""

    qr = ""
    if card.qr_image:
        try:
            qr = request.build_absolute_uri(card.qr_image.url)
        except ValueError:
            qr = ""

    return {
        "card_public_id": str(card.public_id),
        "card_number": card.card_number or "",
        "qr_identifier": card.qr_identifier or "",
        "preview_url": preview_abs,
        "qr_image_url": qr,
        "photo_url": photo,
        "is_blocked": bool(card.is_blocked),
        "is_active": bool(card.is_active),
        "nom": (student.nom or "").strip(),
        "postnom": (student.postnom or "").strip(),
        "prenom": (student.prenom or "").strip(),
        "matricule": student.matricule or "",
        "classe": class_name,
        "section": section,
        "option": option,
        "annee": year_label,
        "school_name": school_display_name(),
        "school_slogan": school_display_slogan(),
        "school_code": getattr(settings, "SCHOOL_CODE", ""),
        "school_city": getattr(settings, "SCHOOL_CITY", ""),
    }


class ParentChildCardAPIView(APIView):
    """Carte d'élève active pour un enfant du responsable."""

    permission_classes = [AllowAny]
    throttle_classes = [ParentChildCardThrottle]
    authentication_classes = []

    def get(self, request, student_public_id):
        guardian, student, error = _load_student_for_guardian(
            request, str(student_public_id)
        )
        if error is not None:
            return error
        assert student is not None and guardian is not None

        card = (
            StudentCard.objects.filter(
                student=student,
                is_active=True,
                is_blocked=False,
            )
            .select_related(
                "student",
                "enrollment__school_class__section",
                "enrollment__school_class__option",
                "enrollment__academic_year",
            )
            .order_by("-generated_at")
            .first()
        )
        if card is None:
            return envelope(
                success=False,
                message="Aucune carte d'élève active pour cet enfant.",
                http_status=404,
            )

        return envelope(
            message="Carte d'élève.",
            data=_serialize_card(card=card, request=request),
        )
