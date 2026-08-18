"""Compact school payment receipt PDF (landscape voucher, B/W + color logo)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path

from django.conf import settings
from reportlab.lib.colors import black, white
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.audit.models import AuditLog
from apps.finance.models import Payment
from apps.finance.services import audit_finance_action
from apps.finance.services.exceptions import FinanceError
from apps.core.branding import school_display_name, school_display_slogan
from apps.finance.services.payment_sequence_service import (
    fee_period_short_label,
    payment_group_label,
)

# Compact landscape slip (school voucher)
RECEIPT_WIDTH = 155 * mm
RECEIPT_HEIGHT = 102 * mm
RECEIPT_SIZE = (RECEIPT_WIDTH, RECEIPT_HEIGHT)

_ONES = (
    "",
    "un",
    "deux",
    "trois",
    "quatre",
    "cinq",
    "six",
    "sept",
    "huit",
    "neuf",
    "dix",
    "onze",
    "douze",
    "treize",
    "quatorze",
    "quinze",
    "seize",
    "dix-sept",
    "dix-huit",
    "dix-neuf",
)
_TENS = (
    "",
    "",
    "vingt",
    "trente",
    "quarante",
    "cinquante",
    "soixante",
    "soixante",
    "quatre-vingt",
    "quatre-vingt",
)


def _school_name() -> str:
    return school_display_name()


def _school_slogan() -> str:
    return school_display_slogan()


def _school_address_line() -> str:
    address = getattr(settings, "SCHOOL_ADDRESS", "") or ""
    city = getattr(settings, "SCHOOL_CITY", "") or ""
    bp = getattr(settings, "SCHOOL_BP", "") or ""
    parts = [p for p in [address, f"B.P. {bp}" if bp else "", city] if p]
    return " · ".join(parts)


def _school_phone() -> str:
    return getattr(settings, "SCHOOL_PHONE", "") or ""


def _logo_path() -> Path | None:
    configured = getattr(settings, "SCHOOL_LOGO", None)
    if configured:
        path = Path(configured)
        if path.exists():
            return path
    fallback = Path(settings.BASE_DIR) / "static" / "src" / "images" / "branding" / "logo.png"
    return fallback if fallback.exists() else None


def _format_money(amount, currency: str) -> str:
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{value:,.2f} {currency}".replace(",", " ")


def _under_100(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    if tens == 7:  # 70-79
        return "soixante-" + _ONES[10 + ones]
    if tens == 9:  # 90-99
        return "quatre-vingt-" + _ONES[10 + ones]
    if tens == 8:
        base = "quatre-vingt"
        if ones == 0:
            return base + "s"
        return f"{base}-{_ONES[ones]}"
    base = _TENS[tens]
    if ones == 0:
        return base
    if ones == 1 and tens in {2, 3, 4, 5, 6}:
        return f"{base} et un"
    return f"{base}-{_ONES[ones]}"


def _under_1000(n: int) -> str:
    if n < 100:
        return _under_100(n)
    hundreds, rest = divmod(n, 100)
    if hundreds == 1:
        head = "cent"
    else:
        head = f"{_ONES[hundreds]} cent"
        if rest == 0:
            head += "s"
    if rest == 0:
        return head
    return f"{head} {_under_100(rest)}"


def amount_in_words_fr(amount, currency: str = "CDF") -> str:
    """French wording for school fee amounts (integer part + currency)."""
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole = int(value)
    cents = int((value - whole) * 100)

    if whole == 0:
        words = "zéro"
    else:
        parts: list[str] = []
        millions, rem = divmod(whole, 1_000_000)
        thousands, units = divmod(rem, 1000)
        if millions:
            if millions == 1:
                parts.append("un million")
            else:
                parts.append(f"{_under_1000(millions)} millions")
        if thousands:
            if thousands == 1:
                parts.append("mille")
            else:
                parts.append(f"{_under_1000(thousands)} mille")
        if units:
            parts.append(_under_1000(units))
        words = " ".join(parts)

    currency_u = (currency or "CDF").upper()
    if currency_u in {"CDF", "FC", "CDF."}:
        unit = "francs congolais"
    elif currency_u == "USD":
        unit = "dollars américains"
    else:
        unit = currency_u

    result = f"{words} {unit}"
    if cents:
        result += f" et {cents:02d} centimes"
    return result.capitalize()


def _student_full_name(payment: Payment) -> str:
    student = payment.student
    return " ".join(
        part for part in [student.nom, student.postnom, student.prenom] if part
    ).strip()


def _payment_purpose(payment: Payment) -> str:
    parts: list[str] = []
    for allocation in payment.allocations.all():
        fee = allocation.obligation.fee
        group = payment_group_label(fee)
        period = fee_period_short_label(fee)
        if group.lower() == period.lower():
            label = group
        else:
            label = f"{group} — {period}"
        parts.append(label)
    return " ; ".join(parts) if parts else "Frais scolaires"


def _draw_hline(pdf: canvas.Canvas, x: float, y: float, width: float) -> None:
    pdf.setStrokeColor(black)
    pdf.setLineWidth(0.6)
    pdf.line(x, y, x + width, y)


def _draw_field_line(
    pdf: canvas.Canvas,
    *,
    label: str,
    value: str,
    x: float,
    y: float,
    width: float,
    label_font: str = "Helvetica-Bold",
    label_size: float = 8,
    value_size: float = 9,
) -> float:
    """Draw label + value on a baseline; return y of the underline."""
    pdf.setFillColor(black)
    pdf.setFont(label_font, label_size)
    pdf.drawString(x, y, label)
    label_w = pdf.stringWidth(label, label_font, label_size)
    pdf.setFont("Helvetica", value_size)
    pdf.drawString(x + label_w + 2 * mm, y, value[:90])
    line_y = y - 1.2 * mm
    _draw_hline(pdf, x, line_y, width)
    return line_y


def build_receipt_pdf(
    *,
    payment: Payment,
    actor=None,
    request=None,
    audit: bool = True,
) -> bytes:
    """Build a compact landscape B/W school receipt (color logo only)."""
    payment = (
        Payment.objects.select_related(
            "enrollment",
            "enrollment__school_class",
            "student",
            "academic_year",
            "recorded_by",
        )
        .prefetch_related("allocations__obligation__fee", "allocations__obligation__fee__category")
        .get(pk=payment.pk)
    )
    if payment.status != Payment.Status.VALID:
        raise FinanceError("Impossible de générer un reçu pour un paiement annulé.")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=RECEIPT_SIZE)
    width, height = RECEIPT_SIZE

    margin = 6 * mm
    content_left = margin
    content_right = width - margin
    content_width = content_right - content_left

    # --- Outer header (outside main box): NO + school strip ---
    header_top = height - 4 * mm
    logo_size = 14 * mm
    logo_x = content_left
    logo_y = header_top - logo_size

    logo_path = _logo_path()
    if logo_path:
        try:
            pdf.drawImage(
                ImageReader(str(logo_path)),
                logo_x,
                logo_y,
                width=logo_size,
                height=logo_size,
                mask="auto",
                preserveAspectRatio=True,
                anchor="c",
            )
        except Exception:
            pass

    text_x = logo_x + logo_size + 3 * mm
    pdf.setFillColor(black)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(text_x, header_top - 4.5 * mm, _school_name().upper())
    pdf.setFont("Helvetica", 6.5)
    pdf.drawString(text_x, header_top - 8 * mm, _school_slogan())
    addr = _school_address_line()
    if addr:
        pdf.drawString(text_x, header_top - 11 * mm, addr[:95])
    phone = _school_phone()
    if phone:
        pdf.drawString(text_x, header_top - 14 * mm, f"Tél. : {phone}"[:95])

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawRightString(content_right, header_top - 4 * mm, f"N° : {payment.receipt_number}")

    # --- Main rounded frame ---
    box_top = logo_y - 2.5 * mm
    box_bottom = 5 * mm
    box_height = box_top - box_bottom
    pdf.setStrokeColor(black)
    pdf.setLineWidth(1.2)
    pdf.setFillColor(white)
    pdf.roundRect(content_left, box_bottom, content_width, box_height, 4 * mm, stroke=1, fill=1)

    inner_left = content_left + 4 * mm
    inner_right = content_right - 4 * mm
    inner_width = inner_right - inner_left
    y = box_top - 5 * mm

    # Title badge "REÇU"
    badge_w = 28 * mm
    badge_h = 6.5 * mm
    badge_x = (width - badge_w) / 2
    badge_y = y - badge_h + 1.5 * mm
    pdf.setFillColor(black)
    pdf.roundRect(badge_x, badge_y, badge_w, badge_h, 1.2 * mm, stroke=0, fill=1)
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(width / 2, badge_y + 2 * mm, "REÇU")

    pdf.setFillColor(black)
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(
        inner_right,
        badge_y + 2.2 * mm,
        f"Date : {payment.payment_date.strftime('%d/%m/%Y')}",
    )

    y = badge_y - 6 * mm
    student_name = _student_full_name(payment)
    classe = str(payment.enrollment.school_class)
    matricule = payment.student.matricule or ""

    _draw_field_line(
        pdf,
        label="Reçu de :",
        value=student_name,
        x=inner_left,
        y=y,
        width=inner_width,
    )
    y -= 7 * mm
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(
        inner_left,
        y,
        f"Matricule : {matricule}    ·    Classe : {classe}    ·    Année : {payment.academic_year.label}",
    )
    _draw_hline(pdf, inner_left, y - 1.2 * mm, inner_width)

    y -= 8 * mm
    words = amount_in_words_fr(payment.amount_total, payment.currency or "CDF")
    _draw_field_line(
        pdf,
        label="La somme de :",
        value=words,
        x=inner_left,
        y=y,
        width=inner_width,
        value_size=7.5,
    )

    currency = payment.currency or "CDF"
    # Remaining on the paid period(s) after this payment (0 if fully settled)
    remaining = Decimal("0.00")
    due_total = Decimal("0.00")
    for allocation in payment.allocations.all():
        obligation = allocation.obligation
        remaining += Decimal(str(obligation.amount_remaining))
        due_total += Decimal(str(obligation.amount_due))

    y -= 7.5 * mm
    paid_txt = _format_money(payment.amount_total, currency)
    rest_txt = _format_money(remaining, currency)
    half = inner_width * 0.48
    _draw_field_line(
        pdf,
        label="Montant payé :",
        value=paid_txt,
        x=inner_left,
        y=y,
        width=half,
        value_size=9,
    )
    _draw_field_line(
        pdf,
        label="Reste dû :",
        value=rest_txt,
        x=inner_left + half + 3 * mm,
        y=y,
        width=inner_width - half - 3 * mm,
        value_size=9,
    )

    y -= 8 * mm
    purpose = _payment_purpose(payment)
    # Wrap purpose on two lines if needed
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(inner_left, y, "Pour paiement de :")
    label_w = pdf.stringWidth("Pour paiement de :", "Helvetica-Bold", 8)
    pdf.setFont("Helvetica", 8)
    purpose_x = inner_left + label_w + 2 * mm
    max_w = inner_right - purpose_x
    if pdf.stringWidth(purpose, "Helvetica", 8) <= max_w:
        pdf.drawString(purpose_x, y, purpose)
        _draw_hline(pdf, inner_left, y - 1.2 * mm, inner_width)
        y -= 7 * mm
    else:
        mid = len(purpose) // 2
        split_at = purpose.rfind(" ", 0, mid + 15)
        if split_at < 10:
            split_at = mid
        line1, line2 = purpose[:split_at].strip(), purpose[split_at:].strip()
        pdf.drawString(purpose_x, y, line1[:70])
        _draw_hline(pdf, inner_left, y - 1.2 * mm, inner_width)
        y -= 6 * mm
        pdf.drawString(inner_left, y, line2[:85])
        _draw_hline(pdf, inner_left, y - 1.2 * mm, inner_width)
        y -= 7 * mm

    # Bottom: mode | signature
    method = payment.get_payment_method_display()
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(inner_left, y, f"Mode : {method}")
    if due_total > 0:
        pdf.setFont("Helvetica", 7)
        pdf.drawString(
            inner_left,
            y - 4.5 * mm,
            f"Montant fixé (période) : {_format_money(due_total, currency)}",
        )

    sig_x = inner_left + inner_width * 0.55
    sig_w = inner_right - sig_x
    sig_line_y = y - 3 * mm
    _draw_hline(pdf, sig_x, sig_line_y, sig_w)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawCentredString(sig_x + sig_w / 2, sig_line_y - 4 * mm, "RECEVEUR")
    recorder = str(payment.recorded_by) if payment.recorded_by_id else ""
    if recorder:
        pdf.setFont("Helvetica", 6.5)
        pdf.drawCentredString(sig_x + sig_w / 2, y + 1.5 * mm, recorder[:36])

    pdf.showPage()
    pdf.save()
    content = buffer.getvalue()
    buffer.close()

    if audit:
        audit_finance_action(
            action=AuditLog.Action.RECEIPT_GENERATED,
            instance=payment,
            description=f"Génération du reçu PDF {payment.receipt_number}",
            actor=actor,
            request=request,
        )
    return content
