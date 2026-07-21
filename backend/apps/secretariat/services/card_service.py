"""Secure student card generation and lifecycle services."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, time
from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.audit.models import AuditLog
from apps.secretariat.models import Enrollment, StudentCard

from . import audit_secretariat_action
from .exceptions import SecretariatError

CARD_SIZE = (85.60 * mm, 53.98 * mm)


def _qr_content(identifier: str) -> ContentFile:
    image = qrcode.make(identifier)
    output = BytesIO()
    image.save(output, format="PNG")
    return ContentFile(output.getvalue())


def _pdf_content(card: StudentCard) -> ContentFile:
    from django.conf import settings

    school_name = getattr(settings, "SCHOOL_NAME", "Institut Kalunga")
    school_slogan = getattr(settings, "SCHOOL_SLOGAN", "La Source du Savoir")
    brand = colors.HexColor("#1f6f4a")

    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=CARD_SIZE)
    width, height = CARD_SIZE
    pdf.setFillColor(brand)
    pdf.rect(0, height - 14 * mm, width, 14 * mm, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(5 * mm, height - 7 * mm, school_name[:34])
    pdf.setFont("Helvetica", 7)
    pdf.drawString(5 * mm, height - 11 * mm, school_slogan[:40])
    pdf.setFillColor(colors.black)
    student = card.student
    full_name = " ".join(p for p in (student.nom, student.postnom, student.prenom) if p)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(5 * mm, height - 20 * mm, full_name[:42])
    pdf.setFont("Helvetica", 8)
    pdf.drawString(5 * mm, height - 25 * mm, f"Matricule : {student.matricule}")
    pdf.drawString(5 * mm, height - 30 * mm, f"Classe : {card.enrollment.school_class.name}")
    pdf.drawString(5 * mm, height - 35 * mm, f"Année : {card.enrollment.academic_year.label}")
    pdf.drawString(5 * mm, height - 40 * mm, f"Carte : {card.card_number}")
    if student.photo:
        try:
            student.photo.open("rb")
            pdf.drawImage(
                ImageReader(student.photo),
                5 * mm,
                6 * mm,
                18 * mm,
                22 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
            student.photo.close()
        except Exception:
            pass
    if card.qr_image:
        card.qr_image.open("rb")
        pdf.drawImage(
            ImageReader(card.qr_image),
            width - 26 * mm,
            6 * mm,
            20 * mm,
            20 * mm,
            preserveAspectRatio=True,
        )
        card.qr_image.close()
    pdf.setStrokeColor(brand)
    pdf.setLineWidth(1)
    pdf.rect(1 * mm, 1 * mm, width - 2 * mm, height - 2 * mm, fill=0, stroke=1)
    pdf.showPage()
    pdf.save()
    return ContentFile(output.getvalue())


@transaction.atomic
def generate_card(
    *,
    enrollment: Enrollment,
    actor=None,
    request=None,
    replace_existing: bool = False,
) -> StudentCard:
    enrollment = Enrollment.objects.select_for_update().select_related(
        "student", "school_class", "academic_year",
    ).get(pk=enrollment.pk)
    if enrollment.status != Enrollment.Status.VALIDATED:
        raise SecretariatError("Une carte exige une inscription validée.")
    if enrollment.student.is_archived:
        raise SecretariatError("Impossible de générer une carte pour un élève archivé.")
    existing = StudentCard.objects.select_for_update().filter(
        enrollment=enrollment,
        is_active=True,
    )
    if existing.exists() and not replace_existing:
        raise SecretariatError("Une carte active existe déjà pour cette inscription.")
    if replace_existing:
        existing.update(is_active=False, is_blocked=True, block_reason="Carte remplacée")

    identifier = f"KAL-CARD-{uuid.uuid4().hex}"
    card = StudentCard(
        student=enrollment.student,
        enrollment=enrollment,
        qr_identifier=identifier,
        card_number=identifier,
        generated_by=actor,
        expires_at=timezone.make_aware(
            datetime.combine(enrollment.academic_year.end_date, time.max),
        ),
    )
    card.qr_image.save(f"{identifier}.png", _qr_content(identifier), save=False)
    card.save()
    card.pdf_file.save(f"{identifier}.pdf", _pdf_content(card), save=True)
    audit_secretariat_action(
        action=AuditLog.Action.CARD_REPLACED if replace_existing else AuditLog.Action.CARD_GENERATED,
        instance=card,
        description=f"{'Remplacement' if replace_existing else 'Génération'} de la carte de {card.student.matricule}",
        actor=actor,
        request=request,
    )
    return card


@transaction.atomic
def block_card(card: StudentCard, *, reason: str, actor=None, request=None) -> StudentCard:
    card = StudentCard.objects.select_for_update().get(pk=card.pk)
    if not reason.strip():
        raise SecretariatError("Le motif du blocage est obligatoire.")
    card.is_blocked = True
    card.is_active = False
    card.block_reason = reason.strip()
    card.save(update_fields=["is_blocked", "is_active", "block_reason", "updated_at"])
    audit_secretariat_action(
        action=AuditLog.Action.CARD_BLOCKED,
        instance=card,
        description=f"Blocage de la carte {card.card_number}",
        actor=actor,
        request=request,
    )
    return card


def replace_card(card: StudentCard, *, reason: str, actor=None, request=None) -> StudentCard:
    with transaction.atomic():
        block_card(card, reason=reason, actor=actor, request=request)
        return generate_card(
            enrollment=card.enrollment,
            actor=actor,
            request=request,
            replace_existing=True,
        )


@transaction.atomic
def batch_generate_cards(
    enrollments: Iterable[Enrollment],
    *,
    actor=None,
    request=None,
) -> list[StudentCard]:
    enrollment_list = list(enrollments)
    ids = [item.pk for item in enrollment_list]
    if len(ids) != len(set(ids)):
        raise SecretariatError("La sélection contient des inscriptions en double.")
    cards = []
    for enrollment in enrollment_list:
        cards.append(generate_card(enrollment=enrollment, actor=actor, request=request))
    return cards
