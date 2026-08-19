"""Guardian (responsable) identification numbers — unique per parent, not per student."""

from __future__ import annotations

import re

from django.db.models import Q

from apps.secretariat.models import Guardian
from apps.secretariat.services.identifier_format import (
    GUARDIAN_MARKER,
    SCHOOL_PREFIX,
    _ELM_PARENT_IDENT_RE,
    _LEGACY_PARENT_IDENT_RE,
    guardian_identification_stem,
    normalize_code,
)

# Legacy compact format: YY + IK + section + option + letter + seq (12 chars)
_LEGACY_IDENT_RE = re.compile(r"^[A-Z0-9]{12}$")
LEGACY_SCHOOL_CODE = "IK"
# Backward compatibility for existing KAL-R IDs in production.
LEGACY_GUARDIAN_SCHOOL_CODE = "KAL"


def generate_guardian_identification(
    *,
    academic_year_start: int,
    section_code: str = "",
    option_code: str = "",
    class_letter: str = "",
    sequence: int,
) -> str:
    """Build a parent ID unique to the responsable (not the student).

    Format: ``ELM{year}R{seq}``
    Example: ``ELM2026R00042``

    Section / option / class are not embedded: a parent may have children
    in several classes.
    """
    del section_code, option_code, class_letter
    stem = guardian_identification_stem(academic_year_start=academic_year_start)
    seq_part = f"{max(1, int(sequence)) % 1_000_000:05d}"
    return f"{stem}{seq_part}"


def generate_legacy_kal_guardian_identification(
    *,
    academic_year_start: int,
    sequence: int,
) -> str:
    """Former KAL-R format kept for migration reference."""
    year_part = int(academic_year_start)
    seq_part = f"{max(1, int(sequence)) % 1_000_000:04d}"
    return f"{LEGACY_GUARDIAN_SCHOOL_CODE}-{year_part}-R-{seq_part}"


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
    section_part = normalize_code(section_code, max_len=1, fallback="X")
    option_part = normalize_code(option_code, max_len=2, fallback="XX")
    letter_part = normalize_code(class_letter, max_len=1, fallback="A")
    seq_part = f"{int(sequence) % 10_000:04d}"
    return f"{year_part}{LEGACY_SCHOOL_CODE}{section_part}{option_part}{letter_part}{seq_part}"


def normalize_identification_number(value: str) -> str:
    """Normalize for comparison; strip spaces, uppercase."""
    raw = (value or "").strip().upper()
    if not raw:
        return ""
    if _LEGACY_PARENT_IDENT_RE.fullmatch(raw.replace(" ", "")):
        return re.sub(r"\s+", "", raw)
    if _ELM_PARENT_IDENT_RE.fullmatch(re.sub(r"[\s\-]", "", raw)):
        return re.sub(r"[\s\-]", "", raw)
    return re.sub(r"[\s\-]", "", raw)


def assert_valid_identification_format(value: str) -> str:
    cleaned = normalize_identification_number(value)
    if not cleaned:
        return ""
    if (
        _ELM_PARENT_IDENT_RE.fullmatch(cleaned)
        or _LEGACY_PARENT_IDENT_RE.fullmatch(cleaned)
        or _LEGACY_IDENT_RE.fullmatch(cleaned)
    ):
        return cleaned
    raise ValueError(
        "Le numéro d'identification du responsable doit être du type "
        "ELM2026R00042 (ou l'ancien format KAL-2026-R-0042)."
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

    elm_match = _ELM_PARENT_IDENT_RE.fullmatch(ident)
    if elm_match:
        stem = f"{SCHOOL_PREFIX}{elm_match.group(1)}{GUARDIAN_MARKER}"
        seq = int(elm_match.group(2))
        width = max(5, len(elm_match.group(2)))
        for offset in range(1, 1_000_000):
            retry = f"{stem}{(seq + offset):0{width}d}"
            if not _taken(retry):
                return retry
        raise ValueError("Impossible de générer un numéro d'identification unique.")

    parent_match = re.fullmatch(r"(KAL-\d{4}-R-)(\d+)", ident, flags=re.IGNORECASE)
    if parent_match:
        prefix, seq = parent_match.group(1).upper(), int(parent_match.group(2))
        width = max(4, len(parent_match.group(2)))
        for offset in range(1, 1_000_000):
            retry = f"{prefix}{(seq + offset):0{width}d}"
            if not _taken(retry):
                return retry
        raise ValueError("Impossible de générer un numéro d'identification unique.")

    prefix = ident[:8]
    for offset in range(1, 10_000):
        retry = f"{prefix}{offset:04d}"
        if not _taken(retry):
            return retry
    raise ValueError("Impossible de générer un numéro d'identification unique.")


def next_guardian_sequence(*, academic_year_start: int) -> int:
    """Next free sequence for parent IDs of the given year."""
    stem = guardian_identification_stem(academic_year_start=academic_year_start)
    latest = (
        Guardian.objects.filter(numero_identification__istartswith=stem)
        .order_by("-numero_identification")
        .values_list("numero_identification", flat=True)
        .first()
    )
    if not latest:
        legacy_stem = f"{LEGACY_GUARDIAN_SCHOOL_CODE}-{int(academic_year_start)}-R-"
        legacy_latest = (
            Guardian.objects.filter(numero_identification__istartswith=legacy_stem)
            .order_by("-numero_identification")
            .values_list("numero_identification", flat=True)
            .first()
        )
        if legacy_latest:
            try:
                return int(str(legacy_latest).rsplit("-", 1)[-1]) + 1
            except (TypeError, ValueError):
                pass
        return max(1, Guardian.objects.count() + 1)
    tail = str(latest)[len(stem) :]
    digits = "".join(ch for ch in tail if ch.isdigit())
    try:
        return int(digits) + 1 if digits else 1
    except ValueError:
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
