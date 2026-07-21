"""Race-safe enrollment number generation."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.secretariat.models import Enrollment, SecretariatSetting


@transaction.atomic
def generate_enrollment_number(*, year: int | None = None) -> str:
    year = year or timezone.localdate().year
    lock, _ = SecretariatSetting.objects.get_or_create(
        key="ENROLLMENT_NUMBER_PREFIX",
        defaults={"value": "INS", "description": "Préfixe des inscriptions"},
    )
    lock = SecretariatSetting.objects.select_for_update().get(pk=lock.pk)
    prefix = lock.value.strip().upper() or "INS"
    stem = f"{prefix}-{year}-"
    latest = (
        Enrollment.objects.select_for_update()
        .filter(enrollment_number__startswith=stem)
        .order_by("-enrollment_number")
        .values_list("enrollment_number", flat=True)
        .first()
    )
    try:
        sequence = int(latest.rsplit("-", 1)[-1]) + 1 if latest else 1
    except ValueError:
        sequence = Enrollment.objects.filter(
            enrollment_number__startswith=stem,
        ).count() + 1
    return f"{stem}{sequence:05d}"
