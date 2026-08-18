"""Resolve students from scanner identifiers (QR or matricule)."""

from __future__ import annotations

from dataclasses import dataclass
import re

from apps.discipline.services.exceptions import DisciplineError
from apps.secretariat.models import AcademicYear, Enrollment, Student, StudentCard

QR_IDENTIFIER_RE = re.compile(r"(KAL-CARD-[0-9a-fA-F]+)")


def normalize_card_qr_payload(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise DisciplineError("Aucun code QR détecté.")
    match = QR_IDENTIFIER_RE.search(value)
    if match:
        return match.group(1)
    if value.upper().startswith("KAL-CARD-"):
        return value
    raise DisciplineError("QR invalide. Carte élève ELIMU attendue.")


@dataclass
class ResolvedStudentIdentity:
    identifier_type: str
    identifier: str
    student: Student
    enrollment: Enrollment
    card: StudentCard | None = None


def resolve_student_identity(*, academic_year: AcademicYear, identifier: str) -> ResolvedStudentIdentity:
    raw = (identifier or "").strip()
    if not raw:
        raise DisciplineError("Identifiant vide.")

    # QR branch
    if "KAL-CARD-" in raw.upper():
        qr = normalize_card_qr_payload(raw)
        card = (
            StudentCard.objects.select_related(
                "student",
                "enrollment",
                "enrollment__academic_year",
                "enrollment__school_class",
            )
            .filter(qr_identifier=qr)
            .first()
        )
        if card is None:
            raise DisciplineError("Aucun élève ne correspond à ce QR.")
        if card.is_blocked:
            raise DisciplineError(card.block_reason or "Cette carte est bloquée.")
        if not card.is_active:
            raise DisciplineError("Cette carte n'est plus active.")
        enrollment = card.enrollment
        if enrollment.academic_year_id != academic_year.id:
            raise DisciplineError(
                "Cette carte appartient à une autre année scolaire "
                f"(carte : «{enrollment.academic_year.label}», année sélectionnée : «{academic_year.label}»). "
                "Changez d'année scolaire ou utilisez la carte de l'année en cours."
            )
        if enrollment.status != Enrollment.Status.VALIDATED:
            raise DisciplineError("Cet élève n'est pas inscrit dans l'année sélectionnée.")
        return ResolvedStudentIdentity(
            identifier_type="qr",
            identifier=qr,
            student=card.student,
            enrollment=enrollment,
            card=card,
        )

    # Matricule branch
    student = Student.objects.filter(matricule__iexact=raw).first()
    if not student:
        raise DisciplineError("Aucun élève ne correspond à ce matricule.")
    enrollment = (
        Enrollment.objects.select_related("student", "school_class", "academic_year")
        .filter(
            student=student,
            academic_year=academic_year,
            status=Enrollment.Status.VALIDATED,
        )
        .first()
    )
    if not enrollment:
        raise DisciplineError("Cet élève n'est pas inscrit dans l'année sélectionnée.")
    return ResolvedStudentIdentity(
        identifier_type="matricule",
        identifier=raw,
        student=student,
        enrollment=enrollment,
    )

