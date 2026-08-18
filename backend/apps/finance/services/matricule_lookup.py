"""Helpers to resolve matricules from a shared prefix + short suffix."""

from __future__ import annotations

from django.utils import timezone

from apps.secretariat.models import Enrollment, SecretariatSetting


def matricule_stem(*, year: int | None = None) -> str:
    """Return the common matricule prefix, e.g. ``KAL-2026-``."""
    year = year or timezone.localdate().year
    prefix_setting = SecretariatSetting.objects.filter(key="MATRICULE_PREFIX").first()
    prefix = (prefix_setting.value if prefix_setting else "KAL").strip().upper() or "KAL"
    return f"{prefix}-{year}-"


def matricule_padding() -> int:
    setting = SecretariatSetting.objects.filter(key="MATRICULE_PADDING").first()
    try:
        return max(1, int(setting.value)) if setting else 5
    except (TypeError, ValueError):
        return 5


def class_matricule_stem(*, school_class) -> str:
    """
    Prefer the shared prefix of students in the class; fallback to year stem.
    """
    year = school_class.academic_year.start_date.year
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

    # Keep a useful stem ending before the numeric identity part when possible.
    if "-" in common:
        # e.g. KAL-2026-00012 → KAL-2026-
        head, _, tail = common.rpartition("-")
        if tail.isdigit() or tail == "":
            return f"{head}-"
        return common if common.endswith("-") else f"{common}"
    # Compact seed style KAL202600012 → keep non-digit prefix
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
    # Allow pasting a full matricule that already includes the stem.
    if stem and suffix.upper().startswith(stem.upper()):
        return suffix.strip().upper()
    digits = "".join(ch for ch in suffix if ch.isdigit())
    if digits and digits == suffix.replace(" ", ""):
        pad = matricule_padding()
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

    # Full matricule pasted
    candidates.append(raw.upper())
    try:
        candidates.append(build_matricule(stem=stem, suffix=raw))
    except ValueError:
        pass
    # Unpadded / alternate padding attempts
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
        # Last resort: suffix match within class/year
        fallback = Enrollment.objects.select_related(
            "student", "school_class", "academic_year"
        ).filter(
            academic_year=academic_year,
            status=Enrollment.Status.VALIDATED,
            student__matricule__iendswith=digits or raw,
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
