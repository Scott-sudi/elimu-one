"""Guardian (responsable) identification numbers — unique per parent, not per student."""

from __future__ import annotations

import re

from django.db.models import Q

from apps.secretariat.models import Guardian

# Legacy compact format: YY + IK + section + option + letter + seq (12 chars)
_LEGACY_IDENT_RE = re.compile(r"^[A-Z0-9]{12}$")
# New parent registry: KAL-2026-R-0042 (distinct from student matricules KAL-2026-#####)
_PARENT_IDENT_RE = re.compile(r"^KAL-\d{4}-R-\d{4,6}$", re.IGNORECASE)
SCHOOL_CODE = "KAL"
LEGACY_SCHOOL_CODE = "IK"


def generate_guardian_identification(
    *,
    academic_year_start: int,
    section_code: str = "",
    option_code: str = "",
    class_letter: str = "",
    sequence: int,
) -> str:
    """Build a parent ID unique to the responsable (not the student).

    Format: ``KAL-{year}-R-{seq}``
    Example: ``KAL-2026-R-0042``

    ``section_code`` / ``option_code`` / ``class_letter`` are accepted for
    backward-compatible call sites but are not embedded in the ID: a parent
    may have children in several classes, so the ID must stay parent-scoped.
    """
    del section_code, option_code, class_letter  # parent-scoped — not class-scoped
    year_part = int(academic_year_start)
    seq_part = f"{max(1, int(sequence)) % 1_000_000:04d}"
    return f"{SCHOOL_CODE}-{year_part}-R-{seq_part}"


def generate_legacy_guardian_identification(
    *,
    academic_year_start: int,
    section_code: str = "",
    option_code: str = "",
    class_letter: str = "",
    sequence: int,
) -> str:
    """Former 12-char format kept for tests / migration reference."""
    year_part = str(academic_year_start)[-2:]
    section_part = (section_code[:1] or "X").upper()
    option_part = (option_code[:2] or "XX").upper()
    letter_part = (class_letter[:1] or "A").upper()
    seq_part = f"{int(sequence) % 10_000:04d}"
    return f"{year_part}{LEGACY_SCHOOL_CODE}{section_part}{option_part}{letter_part}{seq_part}"


def normalize_identification_number(value: str) -> str:
    """Normalize for comparison; keep dashes for the KAL-R format."""
    raw = (value or "").strip().upper()
    if not raw:
        return ""
    if _PARENT_IDENT_RE.fullmatch(raw.replace(" ", "")):
        return re.sub(r"\s+", "", raw)
    # Legacy: strip spaces and dashes
    return re.sub(r"[\s\-]", "", raw)


def assert_valid_identification_format(value: str) -> str:
    cleaned = normalize_identification_number(value)
    if not cleaned:
        return ""
    if _PARENT_IDENT_RE.fullmatch(cleaned) or _LEGACY_IDENT_RE.fullmatch(cleaned):
        return cleaned
    raise ValueError(
        "Le numéro d'identification du responsable doit être du type "
        "KAL-2026-R-0042 (ou l'ancien format 12 caractères)."
    )


def ensure_unique_guardian_identification(
    candidate: str,
    *,
    exclude_pk: int | None = None,
) -> str:
    """Return *candidate* if free, otherwise bump the trailing sequence."""
    ident = assert_valid_identification_format(candidate)
    if not ident:
        raise ValueError("Numéro d'identification vide.")

    def _taken(value: str) -> bool:
        qs = Guardian.objects.filter(
            Q(numero_identification__iexact=value) | Q(numero_identification=value)
        )
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        return qs.exists()

    if not _taken(ident):
        return ident

    # Bump sequence for KAL-YYYY-R-NNNN
    parent_match = re.fullmatch(r"(KAL-\d{4}-R-)(\d+)", ident, flags=re.IGNORECASE)
    if parent_match:
        prefix, seq = parent_match.group(1).upper(), int(parent_match.group(2))
        width = max(4, len(parent_match.group(2)))
        for offset in range(1, 1_000_000):
            retry = f"{prefix}{(seq + offset):0{width}d}"
            if not _taken(retry):
                return retry
        raise ValueError("Impossible de générer un numéro d'identification unique.")

    # Legacy 12-char: bump last 4 digits
    prefix = ident[:8]
    for offset in range(1, 10_000):
        retry = f"{prefix}{offset:04d}"
        if not _taken(retry):
            return retry
    raise ValueError("Impossible de générer un numéro d'identification unique.")


def next_guardian_sequence(*, academic_year_start: int) -> int:
    """Next free sequence for parent IDs of the given year."""
    stem = f"{SCHOOL_CODE}-{int(academic_year_start)}-R-"
    latest = (
        Guardian.objects.filter(numero_identification__istartswith=stem)
        .order_by("-numero_identification")
        .values_list("numero_identification", flat=True)
        .first()
    )
    if not latest:
        # Also count legacy IDs so new sequence stays ahead of total guardians
        return max(1, Guardian.objects.count() + 1)
    try:
        return int(str(latest).rsplit("-", 1)[-1]) + 1
    except (TypeError, ValueError):
        return Guardian.objects.count() + 1


def next_guardian_identification(
    *,
    academic_year_start: int,
    section_code: str = "",
    option_code: str = "",
    class_letter: str = "",
    sequence: int | None = None,
    exclude_pk: int | None = None,
) -> str:
    """Generate and guarantee a unique parent identification number."""
    if sequence is None:
        sequence = next_guardian_sequence(academic_year_start=academic_year_start)
    candidate = generate_guardian_identification(
        academic_year_start=academic_year_start,
        section_code=section_code,
        option_code=option_code,
        class_letter=class_letter,
        sequence=sequence,
    )
    return ensure_unique_guardian_identification(candidate, exclude_pk=exclude_pk)


def suggest_guardian_identification_for_class(*, school_class) -> str:
    """Preview ID for enrollment UI (class year context, parent-scoped sequence)."""
    year = school_class.academic_year
    year_start = year.start_date.year if year and year.start_date else timezone_year()
    section_code = getattr(getattr(school_class, "section", None), "code", "") or ""
    option_code = getattr(getattr(school_class, "option", None), "code", "") or ""
    class_letter = getattr(school_class, "letter", "") or ""
    return next_guardian_identification(
        academic_year_start=year_start,
        section_code=section_code,
        option_code=option_code,
        class_letter=class_letter,
    )


def timezone_year() -> int:
    from django.utils import timezone

    return timezone.localdate().year
