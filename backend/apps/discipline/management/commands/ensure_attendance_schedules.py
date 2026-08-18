"""Ensure default AM/PM attendance schedules exist for open years."""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.discipline.models import AttendanceSchedule
from apps.discipline.services.schedule_service import ensure_default_attendance_schedules
from apps.secretariat.models import AcademicYear


class Command(BaseCommand):
    help = (
        "Crée les horaires avant-midi / après-midi manquants pour les années ouvertes "
        "(nécessaire au pointage QR avec règles de retard)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year-label",
            type=str,
            default="",
            help="Année cible (ex. 2026-2027). Par défaut : année active.",
        )
        parser.add_argument(
            "--strict-hours",
            action="store_true",
            help="Utiliser les horaires réels (fin 12h30 / 18h) au lieu du mode démo 23h59.",
        )

    def handle(self, *args, **options):
        label = (options["year_label"] or "").strip()
        relaxed = not options["strict_hours"] and getattr(settings, "DEBUG", False)

        if label:
            years = list(AcademicYear.objects.filter(label=label, is_closed=False))
        else:
            years = list(
                AcademicYear.objects.filter(is_active=True, is_closed=False)
            ) or list(AcademicYear.objects.filter(is_closed=False).order_by("-start_date")[:1])

        if not years:
            self.stderr.write("Aucune année scolaire ouverte trouvée.")
            return

        actor = User.objects.filter(is_archived=False).order_by("id").first()
        total = 0
        for year in years:
            before = AttendanceSchedule.objects.filter(academic_year=year).count()
            created = ensure_default_attendance_schedules(
                academic_year=year,
                actor=actor,
                relaxed_end_time=relaxed,
            )
            after = AttendanceSchedule.objects.filter(academic_year=year).count()
            mode = "démo (fin 23:59)" if relaxed else "standard"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{year.label} — {len(created)} horaire(s) cree(s) "
                    f"({before} -> {after}, mode {mode})"
                )
            )
            total += len(created)

        if total == 0:
            self.stdout.write("Horaires déjà configurés pour la/les année(s) ciblée(s).")
