"""Helpers to resolve matricules from a shared prefix + short suffix."""

from __future__ import annotations

from django.utils import timezone

from apps.secretariat.models import Enrollment, SecretariatSetting
from apps.secretariat.services.identifier_format import (
    SCHOOL_PREFIX,
    parse_student_matricule_suffix,
    student_matricule_stem,
)


def matricule_prefix() -> str:
    setting = SecretariatSetting.objects.filter(key="MATRICULE_PREFIX").first()
    value = (setting.value if setting else SCHOOL_PREFIX).strip().upper()
    return value or SCHOOL_PREFIX


def matricule_stem(*, year: int | None = None) -> str:
    """Return the year-level prefix, e.g. ``ELM2026`` (legacy: ``KAL-2026-``)."""
    year = year or timezone.localdate().year
    prefix = matricule_prefix()
    if prefix == "KAL":
        return f"{prefix}-{year}-"
    return f"{prefix}{year}"


def matricule_padding() -> int:
    setting = SecretariatSetting.objects.filter(key="MATRICULE_PADDING").first()
    try:
        return max(4, int(setting.value)) if setting else 5
    except (TypeError, ValueError):
        return 5


def class_matricule_stem(*, school_class) -> str:
    """
    Prefer ELM class stem; fall back to common prefix of enrolled students.
    """
    year = school_class.academic_year.start_date.year
    prefix = matricule_prefix()
    if prefix != "KAL":
        return student_matricule_stem(school_class=school_class)

    matricules = list(
        Enrollment.objects.filter(
            school_class=school_class,
            status=Enrollment.Status.VALIDATED,
        ).values_list("student__matricule", flat=True)[:200]
    )
    if not matricules:
        return matricule_stem(year=year)

    common = matricules[0]
    for value in matricules[1:]:
        while common and not value.startswith(common):
            common = common[:-1]
        if not common:
            break

    if "-" in common:
        head, _, tail = common.rpartition("-")
        if tail.isdigit() or tail == "":
            return f"{head}-"
        return common if common.endswith("-") else f"{common}"
    i = len(common)
    while i > 0 and common[i - 1].isdigit():
        i -= 1
    return common[:i] or matricule_stem(year=year)


def build_matricule(*, stem: str, suffix: str) -> str:
    """Join stem + suffix, padding numeric suffixes when useful."""
    stem = (stem or "").strip()
    suffix = (suffix or "").strip()
    if not suffix:
        raise ValueError("Le numéro de matricule est obligatoire.")
    if stem and suffix.upper().startswith(stem.upper()):
        return suffix.strip().upper()
    digits = "".join(ch for ch in suffix if ch.isdigit())
    if digits and digits == suffix.replace(" ", ""):
        pad = matricule_padding()
        if stem.endswith("-"):
            return f"{stem}{int(digits):0{pad}d}"
        return f"{stem}{int(digits):0{pad}d}"
    return f"{stem}{suffix}".upper()


def find_enrollment_by_matricule_suffix(
    *,
    suffix: str,
    academic_year,
    school_class=None,
    stem: str | None = None,
) -> Enrollment:
    """Resolve a validated enrollment from matricule stem + suffix."""
    if school_class is not None and stem is None:
        stem = class_matricule_stem(school_class=school_class)
    if stem is None:
        stem = matricule_stem(year=academic_year.start_date.year)

    candidates = []
    raw = (suffix or "").strip()
    if not raw:
        raise Enrollment.DoesNotExist("Numéro de matricule manquant.")

    candidates.append(raw.upper())
    try:
        candidates.append(build_matricule(stem=stem, suffix=raw))
    except ValueError:
        pass

    identity_suffix = parse_student_matricule_suffix(raw, stem=stem)
    if identity_suffix:
        pad = matricule_padding()
        candidates.append(f"{stem}{identity_suffix}")
        if identity_suffix.isdigit():
            candidates.append(f"{stem}{int(identity_suffix):0{pad}d}")

    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits:
        pad = matricule_padding()
        candidates.append(f"{stem}{digits}")
        candidates.append(f"{stem}{int(digits):0{pad}d}")

    seen = set()
    unique = []
    for item in candidates:
        key = item.upper()
        if key not in seen:
            seen.add(key)
            unique.append(key)

    qs = Enrollment.objects.select_related(
        "student", "school_class", "academic_year"
    ).filter(
        academic_year=academic_year,
        status=Enrollment.Status.VALIDATED,
        student__matricule__in=unique,
    )
    if school_class is not None:
        qs = qs.filter(school_class=school_class)
    enrollment = qs.first()
    if enrollment is None:
        fallback = Enrollment.objects.select_related(
            "student", "school_class", "academic_year"
        ).filter(
            academic_year=academic_year,
            status=Enrollment.Status.VALIDATED,
            student__matricule__iendswith=identity_suffix or digits or raw,
        )
        if school_class is not None:
            fallback = fallback.filter(school_class=school_class)
        enrollment = fallback.first()
    if enrollment is None:
        raise Enrollment.DoesNotExist(
            "Aucun élève trouvé pour ce matricule"
            + (" dans cette classe." if school_class else ".")
        )
    return enrollment
