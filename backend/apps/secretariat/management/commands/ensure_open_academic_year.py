"""Assure qu'il existe au moins une année scolaire ouverte (après purge)."""

from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.secretariat.models import AcademicYear


class Command(BaseCommand):
    help = "Crée une année scolaire ouverte si aucune n'existe (démarrage production)."

    def handle(self, *args, **options):
        open_years = AcademicYear.objects.filter(is_closed=False).count()
        if open_years:
            active = AcademicYear.objects.filter(is_active=True, is_closed=False).first()
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK — année(s) ouverte(s): {open_years}"
                    + (f" | active: {active.label}" if active else "")
                )
            )
            return

        today = timezone.localdate()
        # Entre sept. N et août N+1 → année N-(N+1)
        if today.month >= 9:
            start_y = today.year
        else:
            start_y = today.year - 1
        end_y = start_y + 1
        label = f"{start_y}-{end_y}"
        start = date(start_y, 9, 1)
        end = date(end_y, 8, 31)

        with transaction.atomic():
            AcademicYear.objects.filter(is_active=True).update(is_active=False)
            year = AcademicYear.objects.create(
                label=label,
                start_date=start,
                end_date=end,
                is_active=True,
                is_closed=False,
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"ANNEE_CREEE {year.label} ({year.start_date} → {year.end_date}) active=oui"
            )
        )
