"""Resolve student-card QR identifiers for finance workflows."""

from __future__ import annotations

import re

from django.urls import reverse

from apps.finance.services.exceptions import FinanceError
from apps.secretariat.models import StudentCard

_QR_ID_RE = re.compile(r"(KAL-CARD-[0-9a-fA-F]+)")


def normalize_card_qr_payload(raw: str) -> str:
    """Extract the opaque card QR identifier from a scan payload."""
    value = (raw or "").strip()
    if not value:
        raise FinanceError("Aucun code QR détecté.")
    match = _QR_ID_RE.search(value)
    if match:
        return match.group(1)
    # Allow pasting the raw identifier even if prefix casing differs
    if value.upper().startswith("KAL-CARD-"):
        return value
    raise FinanceError(
        "Ce code QR n'est pas une carte élève Kalunga (identifiant attendu : KAL-CARD-…)."
    )


def resolve_card_qr_for_finance(raw: str) -> dict:
    """
    Map a scanned card QR to the finance student-situation URL.

    Blocked/inactive cards still resolve for consultation (accountant needs history),
    but the response flags the card status.
    """
    identifier = normalize_card_qr_payload(raw)
    card = (
        StudentCard.objects.select_related("student", "enrollment", "enrollment__school_class")
        .filter(qr_identifier=identifier)
        .first()
    )
    if card is None:
        raise FinanceError("Carte introuvable pour ce code QR.")

    student = card.student
    redirect_url = reverse("finance:student-situation", kwargs={"public_id": student.public_id})
    warning = ""
    if card.is_blocked:
        warning = card.block_reason or "Cette carte est bloquée."
    elif not card.is_active:
        warning = "Cette carte n'est plus active."

    return {
        "qr_identifier": card.qr_identifier,
        "card_number": card.card_number,
        "student_public_id": str(student.public_id),
        "matricule": student.matricule,
        "full_name": " ".join(
            part for part in (student.nom, student.postnom, student.prenom) if part
        ),
        "class_name": card.enrollment.school_class.name if card.enrollment_id else "",
        "is_blocked": card.is_blocked,
        "is_active": card.is_active,
        "warning": warning,
        "redirect_url": redirect_url,
    }
