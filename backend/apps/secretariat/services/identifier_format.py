"""ELIMU identifier formats for students and guardians."""

from __future__ import annotations

import re

SCHOOL_PREFIX = "ELM"
GUARDIAN_MARKER = "R"

# Legacy patterns still accepted for lookup / auth.
_LEGACY_STUDENT_PREFIXES = ("KAL", "ENG", "IK")
_LEGACY_PARENT_IDENT_RE = re.compile(r"^KAL-\d{4}-R-\d{4,6}$", re.IGNORECASE)
_ELM_PARENT_IDENT_RE = re.compile(r"^ELM(\d{4})R(\d{4,6})$", re.IGNORECASE)
_ELM_STUDENT_RE = re.compile(r"^ELM(\d{4})([A-Z0-9]{3,})(\d{4,6})$")


def normalize_code(value: str | None, *, max_len: int = 6, fallback: str = "GEN") -> str:
    raw = re.sub(r"[^A-Z0-9]", "", (value or "").strip().upper())
    if not raw:
        return fallback[:max_len]
    return raw[:max_len]


def student_matricule_stem(*, school_class) -> str:
    """
    Prefix before the unique student sequence.

    ELM + year + section + option + class codes (compact, no separators).
    Example stem: ``ELM2026GENSCIA1A`` → ``ELM2026GENSCIA1A00003``.
    """
    year = school_class.academic_year.start_date.year
    section_code = normalize_code(getattr(getattr(school_class, "section", None), "code", None))
    option_code = normalize_code(getattr(getattr(school_class, "option", None), "code", None))
    class_code = normalize_code(
        getattr(school_class, "code", None),
        max_len=8,
        fallback=normalize_code(getattr(school_class, "letter", None), max_len=2, fallback="A"),
    )
    return f"{SCHOOL_PREFIX}{year}{section_code}{option_code}{class_code}"


def provisional_student_matricule_stem(*, year: int) -> str:
    """Students created outside a class inscription (assigned fully on enrollment)."""
    return f"{SCHOOL_PREFIX}{int(year)}GENGENGEN"


def guardian_identification_stem(*, academic_year_start: int) -> str:
    """Example: ``ELM2026R`` → ``ELM2026R00042``."""
    return f"{SCHOOL_PREFIX}{int(academic_year_start)}{GUARDIAN_MARKER}"


def is_legacy_student_matricule(value: str | None) -> bool:
    raw = (value or "").strip().upper()
    if not raw:
        return True
    if raw.startswith(_LEGACY_STUDENT_PREFIXES):
        return True
    if "-" in raw and raw.split("-", 1)[0] in _LEGACY_STUDENT_PREFIXES:
        return True
    return not raw.startswith(SCHOOL_PREFIX)


def is_provisional_student_matricule(value: str | None) -> bool:
    return "GENGENGEN" in (value or "").upper()


def is_elm_student_matricule_for_class(value: str | None, *, school_class) -> bool:
    raw = (value or "").strip().upper()
    if not raw.startswith(SCHOOL_PREFIX):
        return False
    stem = student_matricule_stem(school_class=school_class)
    return raw.startswith(stem)


def parse_student_matricule_suffix(value: str | None, *, stem: str) -> str:
    """Return trailing digits (identity suffix) from a full matricule or partial input."""
    raw = (value or "").strip().upper()
    if not raw:
        return ""
    if stem and raw.startswith(stem.upper()):
        return raw[len(stem) :]
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits
