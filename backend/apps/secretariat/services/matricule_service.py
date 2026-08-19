"""Race-safe student matricule generation (ELIMU format)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.secretariat.models import SecretariatSetting, Student

from .identifier_format import (
    is_elm_student_matricule_for_class,
    is_legacy_student_matricule,
    is_provisional_student_matricule,
    provisional_student_matricule_stem,
    student_matricule_stem,
)


def _matricule_prefix() -> str:
    setting = SecretariatSetting.objects.filter(key="MATRICULE_PREFIX").first()
    value = (setting.value if setting else "ELM").strip().upper()
    return value or "ELM"


def _matricule_padding() -> int:
    setting = SecretariatSetting.objects.filter(key="MATRICULE_PADDING").first()
    try:
        return max(4, int(setting.value)) if setting else 5
    except (TypeError, ValueError):
        return 5


def _next_sequence(*, stem: str, padding: int) -> int:
    latest = (
        Student.objects.filter(matricule__istartswith=stem)
        .order_by("-matricule")
        .values_list("matricule", flat=True)
        .first()
    )
    if not latest:
        return 1
    tail = str(latest)[len(stem) :]
    digits = "".join(ch for ch in tail if ch.isdigit())
    try:
        return int(digits) + 1 if digits else 1
    except ValueError:
        return Student.objects.filter(matricule__istartswith=stem).count() + 1


def _build_unique_matricule(*, stem: str, padding: int) -> str:
    sequence = _next_sequence(stem=stem, padding=padding)
    for _ in range(1_000_000):
        candidate = f"{stem}{sequence:0{padding}d}"
        if not Student.objects.filter(matricule__iexact=candidate).exists():
            return candidate
        sequence += 1
    raise ValueError("Impossible de générer un matricule unique.")


@transaction.atomic
def generate_matricule(*, school_class=None, year: int | None = None) -> str:
    """
    Generate a unique student matricule.

    With ``school_class``: ``ELM{year}{section}{option}{class}{seq}``.
    Without class (provisional): ``ELM{year}GENGENGEN{seq}`` until enrollment.
    """
    SecretariatSetting.objects.select_for_update().get_or_create(
        key="MATRICULE_PREFIX",
        defaults={"value": "ELM", "description": "Préfixe des matricules"},
    )
    padding_setting, _ = SecretariatSetting.objects.get_or_create(
        key="MATRICULE_PADDING",
        defaults={"value": "5", "description": "Longueur du compteur matricule"},
    )
    SecretariatSetting.objects.select_for_update().filter(pk=padding_setting.pk).exists()

    padding = _matricule_padding()
    if school_class is not None:
        stem = student_matricule_stem(school_class=school_class)
    else:
        year = year or timezone.localdate().year
        stem = provisional_student_matricule_stem(year=year)

    return _build_unique_matricule(stem=stem, padding=padding)


@transaction.atomic
def ensure_student_matricule(*, student: Student, school_class) -> Student:
    """
    Assign an ELM class-scoped matricule when missing or still on legacy KAL/ENG.
    """
    student = Student.objects.select_for_update().get(pk=student.pk)
    current = (student.matricule or "").strip()
    if current and is_elm_student_matricule_for_class(current, school_class=school_class):
        return student
    if (
        current
        and not is_legacy_student_matricule(current)
        and not is_provisional_student_matricule(current)
    ):
        return student

    student.matricule = generate_matricule(school_class=school_class)
    student.save(update_fields=["matricule", "updated_at"])
    return student
