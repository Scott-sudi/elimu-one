"""Secure student card generation and lifecycle services.

The printable PDF is a full-bleed image of the card so the exported file
matches the on-screen layout (no scattered ReportLab text boxes).
"""

from __future__ import annotations

import re
import uuid
import zipfile
from collections.abc import Iterable
from datetime import datetime, time
from io import BytesIO
from pathlib import Path

import qrcode
from django.conf import settings
from apps.core.branding import school_display_name, school_display_slogan
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.audit.models import AuditLog
from apps.secretariat.models import AcademicYear, Enrollment, StudentCard

from . import audit_secretariat_action
from .exceptions import SecretariatError

# Petite carte scolaire paysage : un peu plus large, moins haute
# (proche d'une carte d'identité / électeur plastique, format poche).
CARD_WIDTH_MM = 105
CARD_HEIGHT_MM = 66
CARD_SIZE = (CARD_WIDTH_MM * mm, CARD_HEIGHT_MM * mm)
DPI = 300

BRAND = (18, 18, 18)  # Noir (plus de vert sur la carte)
BRAND_DARK = (0, 0, 0)
INK = (26, 26, 26)
MUTED = (75, 85, 99)
PANEL = (243, 246, 244)
WHITE = (255, 255, 255)


def _mm_to_px(value_mm: float) -> int:
    return int(round(value_mm / 25.4 * DPI))


def _qr_content(identifier: str) -> ContentFile:
    image = qrcode.make(identifier, border=1)
    output = BytesIO()
    image.save(output, format="PNG")
    return ContentFile(output.getvalue())


def _next_card_number(*, year: int) -> str:
    stem = f"CRD{year}-"
    latest = (
        StudentCard.objects.filter(card_number__startswith=stem)
        .order_by("-card_number")
        .values_list("card_number", flat=True)
        .first()
    )
    sequence = 1
    if latest:
        try:
            sequence = int(str(latest).split("-")[-1]) + 1
        except ValueError:
            sequence = StudentCard.objects.filter(card_number__startswith=stem).count() + 1
    return f"{stem}{sequence:05d}"


def _logo_path() -> Path | None:
    configured = getattr(settings, "SCHOOL_LOGO", None)
    if configured:
        path = Path(configured)
        if path.exists():
            return path
    fallback = Path(settings.BASE_DIR) / "static" / "src" / "images" / "branding" / "logo.png"
    return fallback if fallback.exists() else None


def _load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = []
    windir = Path(__import__("os").environ.get("WINDIR", r"C:\Windows"))
    fonts = windir / "Fonts"
    if bold:
        candidates.extend(
            [
                fonts / "arialbd.ttf",
                fonts / "segoeuib.ttf",
                fonts / "calibrib.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                fonts / "arial.ttf",
                fonts / "segoeui.ttf",
                fonts / "calibri.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        )
    for path in candidates:
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    value = (text or "—").strip() or "—"
    if draw.textlength(value, font=font) <= max_width:
        return value
    ellipsis = "…"
    while value and draw.textlength(value + ellipsis, font=font) > max_width:
        value = value[:-1]
    return (value + ellipsis) if value else ellipsis


def _open_image(source) -> Image.Image | None:
    try:
        if source is None:
            return None
        if hasattr(source, "path") and callable(getattr(source, "open", None)):
            # Django FieldFile
            source.open("rb")
            try:
                return Image.open(source).convert("RGBA")
            finally:
                try:
                    source.close()
                except Exception:
                    pass
        return Image.open(str(source)).convert("RGBA")
    except Exception:
        return None


def _circular_logo(source: Image.Image, size: int) -> Image.Image:
    """Circular logo exactly like the login page (round plate, no white rectangle)."""
    # White disc (login uses background #fff + border-radius 50%)
    plate = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(plate).ellipse((0, 0, size - 1, size - 1), fill=(255, 255, 255, 255))

    # Cover + slight zoom like .login-card__logo img { object-fit: cover; transform: scale(1.06) }
    zoomed = int(round(size * 1.06))
    fitted = ImageOps.fit(source.convert("RGBA"), (zoomed, zoomed), method=Image.Resampling.LANCZOS)
    offset = (zoomed - size) // 2
    fitted = fitted.crop((offset, offset, offset + size, offset + size))

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    plate.paste(fitted, (0, 0), mask=mask)

    # Soft white ring (login border)
    ImageDraw.Draw(plate).ellipse(
        (1, 1, size - 2, size - 2),
        outline=(255, 255, 255, 230),
        width=max(2, size // 28),
    )
    return plate


def _paste_cover(base: Image.Image, source: Image.Image, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    target_w, target_h = x1 - x0, y1 - y0
    fitted = ImageOps.fit(source.convert("RGB"), (target_w, target_h), method=Image.Resampling.LANCZOS)
    if base.mode == "RGBA":
        base.paste(fitted, (x0, y0))
    else:
        base.paste(fitted, (x0, y0))


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    *,
    fill=None,
    outline=None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _render_card_image(card: StudentCard) -> Image.Image:
    """Card layout restored (readable spacing) — only color=black and round logo changed."""
    width = _mm_to_px(CARD_WIDTH_MM)
    height = _mm_to_px(CARD_HEIGHT_MM)
    margin = _mm_to_px(3.5)
    image = Image.new("RGBA", (width, height), (*WHITE, 255))
    draw = ImageDraw.Draw(image)

    school_name = school_display_name()
    school_slogan = school_display_slogan()
    school_code = getattr(settings, "SCHOOL_CODE", "")
    school_city = getattr(settings, "SCHOOL_CITY", "")

    enrollment = card.enrollment
    school_class = enrollment.school_class
    student = card.student
    section_name = school_class.section.name if school_class.section_id else "Tronc commun"
    option_name = school_class.option.name if school_class.option_id else "—"
    year_label = enrollment.academic_year.label

    # Larger, clearer typography
    font_school = _load_font(36, bold=True)
    font_slogan = _load_font(22)
    font_meta = _load_font(20)
    font_label = _load_font(16)
    font_value = _load_font(24, bold=True)
    font_footer = _load_font(20, bold=True)
    font_hint = _load_font(14)
    font_initials = _load_font(38, bold=True)

    header_h = _mm_to_px(16.5)
    draw.rectangle((0, 0, width, header_h), fill=BRAND)

    # Round logo (login style) — visible on black header
    logo_box = _mm_to_px(12)
    logo_x = margin
    logo_y = (header_h - logo_box) // 2
    logo = _open_image(_logo_path()) if _logo_path() else None
    if logo:
        image.alpha_composite(_circular_logo(logo, logo_box), dest=(logo_x, logo_y))

    text_x = logo_x + logo_box + _mm_to_px(3)
    draw.text((text_x, _mm_to_px(3.6)), school_name.upper()[:32], font=font_school, fill=WHITE)
    draw.text((text_x, _mm_to_px(9.6)), school_slogan[:38], font=font_slogan, fill=WHITE)

    meta_right = width - margin
    code_text = f"Code {school_code}"
    draw.text((meta_right - draw.textlength(code_text, font=font_meta), _mm_to_px(3.8)), code_text, font=font_meta, fill=WHITE)
    draw.text((meta_right - draw.textlength(school_city, font=font_meta), _mm_to_px(9.6)), school_city, font=font_meta, fill=WHITE)

    footer_h = _mm_to_px(8)
    footer_y = height - footer_h
    draw.rectangle((0, footer_y, width, height), fill=PANEL)
    footer = f"Carte N° {card.card_number}"
    fw = draw.textlength(footer, font=font_footer)
    draw.text(((width - fw) / 2, footer_y + _mm_to_px(2.2)), footer, font=font_footer, fill=INK)

    # Fine gray separators — inset so they never overrun the outer contour
    sep = max(1, _mm_to_px(0.3))
    sep_inset = _mm_to_px(1.6)
    sep_gray = (168, 168, 168)
    draw.rectangle((sep_inset, header_h, width - sep_inset, header_h + sep), fill=sep_gray)
    draw.rectangle((sep_inset, footer_y - sep, width - sep_inset, footer_y), fill=sep_gray)

    body_top = header_h + sep + _mm_to_px(3.2)
    body_bottom = footer_y - sep - _mm_to_px(3.2)

    photo_w = _mm_to_px(24)
    photo_h = _mm_to_px(30)
    photo_x = margin
    photo_y = body_top + ((body_bottom - body_top) - photo_h) // 2
    photo_box = (photo_x, photo_y, photo_x + photo_w, photo_y + photo_h)
    _draw_rounded_rect(draw, photo_box, radius=_mm_to_px(1.2), fill=PANEL, outline=BRAND, width=2)

    photo = _open_image(student.photo) if student.photo else None
    if photo:
        inset = _mm_to_px(1)
        _paste_cover(
            image,
            photo,
            (photo_x + inset, photo_y + inset, photo_x + photo_w - inset, photo_y + photo_h - inset),
        )
        _draw_rounded_rect(draw, photo_box, radius=_mm_to_px(1.2), outline=BRAND, width=2)
    else:
        initials = "".join(part[0] for part in (student.prenom, student.nom) if part).upper()[:2] or "?"
        iw = draw.textlength(initials, font=font_initials)
        draw.text((photo_x + (photo_w - iw) / 2, photo_y + photo_h / 2 - _mm_to_px(5)), initials, font=font_initials, fill=MUTED)
        hint = "Photo passeport"
        hw = draw.textlength(hint, font=font_hint)
        draw.text((photo_x + (photo_w - hw) / 2, photo_y + photo_h - _mm_to_px(5.5)), hint, font=font_hint, fill=MUTED)

    qr_size = _mm_to_px(24)
    qr_x = width - margin - qr_size
    qr_y = photo_y + (photo_h - qr_size) // 2
    qr_img = _open_image(card.qr_image) if card.qr_image else None
    if qr_img:
        _paste_cover(image, qr_img, (qr_x, qr_y, qr_x + qr_size, qr_y + qr_size))
    scan = "Scanner"
    sw = draw.textlength(scan, font=font_hint)
    draw.text((qr_x + (qr_size - sw) / 2, qr_y + qr_size + _mm_to_px(1.2)), scan, font=font_hint, fill=MUTED)

    # Two clear columns with breathing room
    fields_left = photo_x + photo_w + _mm_to_px(4.5)
    fields_right_limit = qr_x - _mm_to_px(4.5)
    col_gap = _mm_to_px(4.5)
    col_w = max(40, (fields_right_limit - fields_left - col_gap) // 2)
    left_col_x = fields_left
    right_col_x = fields_left + col_w + col_gap
    row_h = _mm_to_px(8.4)
    start_y = body_top + _mm_to_px(0.8)

    left_fields = [
        ("Nom", student.nom),
        ("Postnom", student.postnom or "—"),
        ("Prénom", student.prenom),
        ("Matricule", student.matricule),
    ]
    right_fields = [
        ("Classe", school_class.name),
        ("Section", section_name),
        ("Option", option_name),
        ("Année", year_label),
    ]

    for index, ((left_label, left_value), (right_label, right_value)) in enumerate(
        zip(left_fields, right_fields)
    ):
        y = start_y + index * row_h
        draw.text((left_col_x, y), left_label.upper(), font=font_label, fill=MUTED)
        draw.text(
            (left_col_x, y + _mm_to_px(3.6)),
            _fit_text(draw, left_value, font_value, col_w - 6),
            font=font_value,
            fill=INK,
        )
        draw.text((right_col_x, y), right_label.upper(), font=font_label, fill=MUTED)
        draw.text(
            (right_col_x, y + _mm_to_px(3.6)),
            _fit_text(draw, right_value, font_value, col_w - 6),
            font=font_value,
            fill=INK,
        )

    # Thin outer border
    border = _mm_to_px(0.7)
    _draw_rounded_rect(
        draw,
        (border, border, width - border, height - border),
        radius=_mm_to_px(1.8),
        outline=BRAND,
        width=2,
    )
    return image.convert("RGB")


def _card_png_bytes(card: StudentCard) -> bytes:
    buffer = BytesIO()
    _render_card_image(card).save(buffer, format="PNG", dpi=(DPI, DPI))
    return buffer.getvalue()


def _save_card_preview(card: StudentCard, png_bytes: bytes) -> str:
    from django.core.files.storage import default_storage

    path = card_preview_path(card)
    if default_storage.exists(path):
        default_storage.delete(path)
    saved = default_storage.save(path, ContentFile(png_bytes))
    return default_storage.url(saved)


def card_preview_path(card: StudentCard) -> str:
    return f"students/cards/preview/{card.qr_identifier}.png"


def card_preview_url(card: StudentCard) -> str | None:
    from django.core.files.storage import default_storage

    path = card_preview_path(card)
    if default_storage.exists(path):
        return default_storage.url(path)
    return None


def _preview_is_stale(card: StudentCard, preview_path: str) -> bool:
    """True when the student photo was updated after the cached PNG was written."""
    from django.core.files.storage import default_storage

    photo = getattr(card.student, "photo", None)
    if not photo or not getattr(photo, "name", None):
        return False
    try:
        if not default_storage.exists(photo.name):
            return True
        preview_mtime = default_storage.get_modified_time(preview_path)
        photo_mtime = default_storage.get_modified_time(photo.name)
        return photo_mtime > preview_mtime
    except Exception:
        return True


def ensure_card_png(card: StudentCard, *, force: bool = False) -> tuple[str, bytes]:
    """Ensure the PNG preview exists and return (storage_path, png_bytes).

    Regenerates when missing, forced, or when the student photo changed after
    the last preview was written.
    """
    from django.core.files.storage import default_storage

    path = card_preview_path(card)
    if (
        not force
        and default_storage.exists(path)
        and not _preview_is_stale(card, path)
    ):
        with default_storage.open(path, "rb") as handle:
            return path, handle.read()
    png_bytes = _card_png_bytes(card)
    _save_card_preview(card, png_bytes)
    return path, png_bytes


def refresh_cards_for_student(student, *, actor=None, request=None) -> int:
    """Rebuild PNG/PDF for every card of this student (e.g. after photo update)."""
    cards = (
        StudentCard.objects.filter(student=student)
        .select_related(
            "student",
            "enrollment__school_class__section",
            "enrollment__school_class__option",
            "enrollment__academic_year",
        )
        .order_by("-generated_at")
    )
    refreshed = 0
    for card in cards:
        refresh_card_pdf(card)
        refreshed += 1
    return refreshed


def card_png_filename(card: StudentCard) -> str:
    matricule = card.student.matricule.replace("/", "-")
    return f"carte_{matricule}_{card.card_number}.png"


def _safe_zip_stem(value: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", value.strip(), flags=re.UNICODE)
    return cleaned.strip("_") or "classe"


def class_cards_zip_filename(school_class) -> str:
    stem = _safe_zip_stem(getattr(school_class, "code", "") or getattr(school_class, "name", "classe"))
    return f"cartes_{stem}.zip"


def build_class_cards_zip(
    school_class,
    *,
    actor=None,
    request=None,
    generate_missing: bool = True,
) -> tuple[bytes, int]:
    """Build a ZIP of PNG cards for all validated enrollments in a class.

    Returns (zip_bytes, card_count). Missing active cards are generated when
    ``generate_missing`` is True.
    """
    enrollments = (
        Enrollment.objects.filter(
            school_class=school_class,
            status=Enrollment.Status.VALIDATED,
        )
        .select_related("student", "school_class", "academic_year")
        .prefetch_related("cards")
        .order_by("student__nom", "student__postnom", "student__prenom")
    )
    buffer = BytesIO()
    count = 0
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        used_names: set[str] = set()
        for enrollment in enrollments:
            card = next(
                (c for c in enrollment.cards.all() if c.is_active and not c.is_blocked),
                None,
            )
            if card is None:
                # Closed-year / blocked cards remain printable for archives.
                card = next(iter(enrollment.cards.all()), None)
            if card is None and generate_missing:
                card = generate_card(enrollment=enrollment, actor=actor, request=request)
            if card is None:
                continue
            _, png_bytes = ensure_card_png(card)
            filename = card_png_filename(card)
            if filename in used_names:
                stem = Path(filename).stem
                filename = f"{stem}_{card.public_id.hex[:8]}.png"
            used_names.add(filename)
            archive.writestr(filename, png_bytes)
            count += 1
    if count == 0:
        raise SecretariatError("Aucune carte à télécharger pour cette classe.")
    return buffer.getvalue(), count


def _pdf_content(card: StudentCard, *, png_bytes: bytes | None = None) -> ContentFile:
    """Build a one-page PDF that embeds the card image at exact physical size."""
    if png_bytes is None:
        png_bytes = _card_png_bytes(card)
    png_buffer = BytesIO(png_bytes)

    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=CARD_SIZE)
    pdf.drawImage(
        ImageReader(png_buffer),
        0,
        0,
        width=CARD_SIZE[0],
        height=CARD_SIZE[1],
        preserveAspectRatio=False,
        mask="auto",
    )
    pdf.showPage()
    pdf.save()
    return ContentFile(pdf_buffer.getvalue())


def refresh_card_pdf(card: StudentCard) -> StudentCard:
    """Regenerate the printable PDF/PNG without changing the QR identifier."""
    card = StudentCard.objects.select_related(
        "student",
        "enrollment__school_class__section",
        "enrollment__school_class__option",
        "enrollment__academic_year",
    ).get(pk=card.pk)
    png_bytes = _card_png_bytes(card)
    _save_card_preview(card, png_bytes)
    filename = Path(card.pdf_file.name).name if card.pdf_file else f"{card.qr_identifier}.pdf"
    card.pdf_file.save(filename, _pdf_content(card, png_bytes=png_bytes), save=True)
    return card


@transaction.atomic
def generate_card(
    *,
    enrollment: Enrollment,
    actor=None,
    request=None,
    replace_existing: bool = False,
) -> StudentCard:
    enrollment = Enrollment.objects.select_for_update().select_related(
        "student",
        "school_class",
        "school_class__section",
        "school_class__option",
        "academic_year",
    ).get(pk=enrollment.pk)
    if enrollment.status != Enrollment.Status.VALIDATED:
        raise SecretariatError("Une carte exige une inscription validée.")
    if enrollment.student.is_archived:
        raise SecretariatError("Impossible de générer une carte pour un élève archivé.")
    if not enrollment.school_class.is_active:
        raise SecretariatError(
            "Cette classe est désactivée. Consultation uniquement — aucune modification n'est possible."
        )
    existing = StudentCard.objects.select_for_update().filter(
        enrollment=enrollment,
        is_active=True,
    )
    if existing.exists() and not replace_existing:
        raise SecretariatError("Une carte active existe déjà pour cette inscription.")
    if replace_existing:
        existing.update(is_active=False, is_blocked=True, block_reason="Carte remplacée")

    identifier = f"KAL-CARD-{uuid.uuid4().hex}"
    card_number = _next_card_number(year=enrollment.academic_year.start_date.year)
    card = StudentCard(
        student=enrollment.student,
        enrollment=enrollment,
        qr_identifier=identifier,
        card_number=card_number,
        generated_by=actor,
        expires_at=timezone.make_aware(
            datetime.combine(enrollment.academic_year.end_date, time.max),
        ),
    )
    card.qr_image.save(f"{identifier}.png", _qr_content(identifier), save=False)
    card.save()
    card = StudentCard.objects.select_related(
        "student",
        "enrollment__school_class__section",
        "enrollment__school_class__option",
        "enrollment__academic_year",
    ).get(pk=card.pk)
    png_bytes = _card_png_bytes(card)
    _save_card_preview(card, png_bytes)
    card.pdf_file.save(f"{identifier}.pdf", _pdf_content(card, png_bytes=png_bytes), save=True)
    audit_secretariat_action(
        action=AuditLog.Action.CARD_REPLACED if replace_existing else AuditLog.Action.CARD_GENERATED,
        instance=card,
        description=f"{'Remplacement' if replace_existing else 'Génération'} de la carte de {card.student.matricule}",
        actor=actor,
        request=request,
    )
    return card


@transaction.atomic
def block_cards_for_academic_year(
    year: AcademicYear,
    *,
    actor=None,
    request=None,
) -> int:
    """Block all still-valid cards of a closed academic year (QR no longer usable)."""
    reason = f"Année scolaire {year.label} clôturée — carte non valide pour l'année en cours."
    now = timezone.now()
    count = StudentCard.objects.filter(
        enrollment__academic_year=year,
        is_blocked=False,
    ).update(
        is_blocked=True,
        is_active=False,
        block_reason=reason,
        updated_at=now,
    )
    if count:
        audit_secretariat_action(
            action=AuditLog.Action.CARD_BLOCKED,
            instance=year,
            description=(
                f"Blocage de {count} carte(s) d'élève suite à la clôture de {year.label}"
            ),
            actor=actor,
            request=request,
            new_values={"blocked_cards": count, "reason": reason},
        )
    return count


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
