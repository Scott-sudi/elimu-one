"""PDF export for student disciplinary files (ReportLab A4)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.conf import settings
from apps.core.branding import school_display_name, school_display_slogan
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.discipline.services.disciplinary_file_service import DisciplinaryFileData


def _school_logo_path() -> Path | None:
    configured = getattr(settings, "SCHOOL_LOGO", None)
    if configured:
        path = Path(configured)
        if path.exists():
            return path
    fallback = Path(settings.BASE_DIR) / "static" / "src" / "images" / "branding" / "logo.png"
    return fallback if fallback.exists() else None


def build_disciplinary_file_pdf(dossier: DisciplinaryFileData, *, generated_by: str = "") -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 18 * mm

    logo = _school_logo_path()
    if logo:
        try:
            c.drawImage(ImageReader(str(logo)), 18 * mm, y - 16 * mm, width=18 * mm, height=18 * mm, mask="auto")
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40 * mm, y - 4 * mm, school_display_name())
    c.setFont("Helvetica", 9)
    c.drawString(40 * mm, y - 9 * mm, school_display_slogan())
    address = getattr(settings, "SCHOOL_ADDRESS", "") or ""
    phone = getattr(settings, "SCHOOL_PHONE", "") or ""
    city = getattr(settings, "SCHOOL_CITY", "") or ""
    c.drawRightString(width - 18 * mm, y - 4 * mm, address)
    c.drawRightString(width - 18 * mm, y - 9 * mm, f"{city}  {phone}".strip())

    y -= 28 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, y, "DOSSIER DISCIPLINAIRE DE L'ÉLÈVE")
    y -= 7 * mm
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, y, f"Référence : {dossier.reference}")
    y -= 5 * mm
    c.drawCentredString(width / 2, y, f"Année scolaire : {dossier.academic_year.label}")

    student = dossier.student
    enrollment = dossier.enrollment
    y -= 14 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, y, "IDENTITÉ")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    lines = [
        f"Matricule : {student.matricule}",
        f"Nom complet : {student.nom} {student.postnom} {student.prenom}".strip(),
        f"Sexe : {student.get_sexe_display()}    Naissance : {student.date_naissance:%d/%m/%Y}",
        f"Classe : {enrollment.school_class.name}",
        f"Statut de suivi : {dossier.followup_status_label}",
    ]
    for line in lines:
        c.drawString(18 * mm, y, line)
        y -= 5 * mm

    stats = dossier.attendance_stats
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, y, "RÉSUMÉ")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    summary_lines = [
        f"Présences : {stats['present']}    Retards : {stats['late']} ({stats['late_minutes']} min)",
        f"Absences : {stats['absent']}    Injustifiées : {stats['unjustified']}",
        f"Incidents ouverts : {stats['open_incidents']} / total {stats['total_incidents']}",
        f"Convocations en attente : {stats['pending_summons']}    Mesures en cours : {stats['active_measures']}",
    ]
    for line in summary_lines:
        c.drawString(18 * mm, y, line)
        y -= 5 * mm

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, y, "CONVOCATIONS")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    c.drawString(
        18 * mm,
        y,
        f"Nombre de convocations des responsables : {stats.get('total_summons', 0)} (en attente : {stats.get('pending_summons', 0)})",
    )

    y = max(y - 14 * mm, 30 * mm)
    c.setFont("Helvetica", 8)
    c.drawString(18 * mm, y, f"Document généré par : {generated_by or '—'}")
    y -= 12 * mm
    c.drawString(18 * mm, y, "Agent de discipline : ____________________")
    c.drawString(110 * mm, y, "Direction : ____________________")

    c.showPage()
    c.save()
    return buffer.getvalue()
