"""Race-safe student matricule generation."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.secretariat.models import SecretariatSetting, Student


@transaction.atomic
def generate_matricule(*, year: int | None = None) -> str:
    year = year or timezone.localdate().year
    prefix_setting, _ = SecretariatSetting.objects.get_or_create(
        key="MATRICULE_PREFIX",
        defaults={"value": "KAL", "description": "Préfixe des matricules"},
    )
    prefix_setting = SecretariatSetting.objects.select_for_update().get(
        pk=prefix_setting.pk,
    )
    padding_setting, _ = SecretariatSetting.objects.get_or_create(
        key="MATRICULE_PADDING",
        defaults={"value": "5", "description": "Longueur du compteur matricule"},
    )
    prefix = prefix_setting.value.strip().upper() or "KAL"
    try:
        padding = max(1, int(padding_setting.value))
    except (TypeError, ValueError):
        padding = 5

    stem = f"{prefix}-{year}-"
    latest = (
        Student.objects.select_for_update()
        .filter(matricule__startswith=stem)
        .order_by("-matricule")
        .values_list("matricule", flat=True)
        .first()
    )
    try:
        sequence = int(latest.rsplit("-", 1)[-1]) + 1 if latest else 1
    except ValueError:
        sequence = Student.objects.filter(matricule__startswith=stem).count() + 1
    return f"{stem}{sequence:0{padding}d}"
