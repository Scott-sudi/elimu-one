"""Seed discipline demo data (attendance, incidents, parent summons)."""

from __future__ import annotations

import random
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.discipline.models import (
    ConductCategory,
    DailyAttendance,
    DisciplinaryIncident,
    ParentSummons,
)
from apps.secretariat.models import AcademicYear, Enrollment


INCIDENT_TITLES = (
    "Retard répété",
    "Tenue scolaire non conforme",
    "Bavardages en classe",
    "Absence non justifiée",
    "Usage du téléphone",
    "Insolence envers un enseignant",
    "Bagarre dans la cour",
)

SUMMONS_REASONS = (
    "Suivi du comportement",
    "Absences répétées",
    "Résultats scolaires",
    "Incident disciplinaire",
    "Paiement du minerval",
)


def _rng_for_year(label: str) -> random.Random:
    return random.Random(f"discipline-{label}")


class Command(BaseCommand):
    help = "Peuple la discipline (présences, incidents, convocations) pour les années scolaires."

    def add_arguments(self, parser):
        parser.add_argument(
            "--years",
            type=int,
            default=6,
            help="Nombre d'années récentes à peupler (défaut: 6).",
        )
        parser.add_argument(
            "--days-per-year",
            type=int,
            default=18,
            help="Jours de présence simulés par année (défaut: 18).",
        )

    def handle(self, *args, **options):
        years_count = options["years"]
        days_per_year = options["days_per_year"]
        actor = User.objects.filter(is_archived=False).order_by("id").first()
        categories = self._ensure_categories()

        years = list(
            AcademicYear.objects.order_by("-start_date")[:years_count]
        )
        if not years:
            self.stderr.write("Aucune année scolaire trouvée.")
            return

        with transaction.atomic():
            DailyAttendance.objects.all().delete()
            ParentSummons.objects.all().delete()
            DisciplinaryIncident.objects.all().delete()

            total_attendance = 0
            total_incidents = 0
            total_summons = 0
            for year in reversed(years):
                rng = _rng_for_year(year.label)
                enrollments = list(
                    Enrollment.objects.filter(
                        academic_year=year,
                        status=Enrollment.Status.VALIDATED,
                    ).select_related("student", "school_class")
                )
                if not enrollments:
                    continue
                att, inc, summ = self._seed_year(
                    year=year,
                    enrollments=enrollments,
                    categories=categories,
                    rng=rng,
                    days=days_per_year,
                    actor=actor,
                )
                total_attendance += att
                total_incidents += inc
                total_summons += summ
                self.stdout.write(
                    f"  - {year.label}: {att} présences, {inc} incidents, {summ} convocations"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Discipline seed OK — {total_attendance} présences, "
                f"{total_incidents} incidents, {total_summons} convocations."
            )
        )

    def _ensure_categories(self) -> list[ConductCategory]:
        specs = (
            ("RETARD", "Retard", ConductCategory.ObservationType.NEGATIVE),
            ("ABSENCE", "Absence injustifiée", ConductCategory.ObservationType.NEGATIVE),
            ("TENUE", "Tenue non conforme", ConductCategory.ObservationType.NEGATIVE),
            ("BAVARDAGE", "Bavardage", ConductCategory.ObservationType.NEGATIVE),
            ("INSOLENCE", "Insolence", ConductCategory.ObservationType.NEGATIVE),
            ("BON_COMPORT", "Bon comportement", ConductCategory.ObservationType.POSITIVE),
        )
        categories: list[ConductCategory] = []
        for code, name, obs_type in specs:
            cat, _ = ConductCategory.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "observation_type": obs_type,
                    "default_severity": ConductCategory.Severity.MODERATE,
                    "is_active": True,
                },
            )
            categories.append(cat)
        return categories

    def _seed_year(
        self,
        *,
        year: AcademicYear,
        enrollments: list[Enrollment],
        categories: list[ConductCategory],
        rng: random.Random,
        days: int,
        actor: User | None,
    ) -> tuple[int, int, int]:
        att_count = 0
        inc_count = 0
        summ_count = 0
        school_days = self._school_days(year, count=days, rng=rng)
        negative_cats = [c for c in categories if c.observation_type == ConductCategory.ObservationType.NEGATIVE]

        for day in school_days:
            sample = rng.sample(enrollments, k=max(1, int(len(enrollments) * rng.uniform(0.55, 0.92))))
            for enrollment in sample:
                roll = rng.random()
                if roll < 0.82:
                    status = DailyAttendance.Status.PRESENT
                elif roll < 0.90:
                    status = DailyAttendance.Status.LATE
                elif roll < 0.96:
                    status = DailyAttendance.Status.ABSENT
                else:
                    status = DailyAttendance.Status.JUSTIFIED_ABSENCE

                DailyAttendance.objects.create(
                    academic_year=year,
                    enrollment=enrollment,
                    student=enrollment.student,
                    date=day,
                    status=status,
                    source=DailyAttendance.Source.MANUAL,
                    arrival_time=time(7, rng.randint(20, 55)) if status == DailyAttendance.Status.LATE else None,
                    late_minutes=rng.randint(5, 35) if status == DailyAttendance.Status.LATE else 0,
                    recorded_by=actor,
                )
                att_count += 1

        incident_sample = rng.sample(
            enrollments,
            k=max(2, int(len(enrollments) * rng.uniform(0.04, 0.09))),
        )
        for idx, enrollment in enumerate(incident_sample):
            category = rng.choice(negative_cats)
            incident = DisciplinaryIncident.objects.create(
                academic_year=year,
                student=enrollment.student,
                school_class=enrollment.school_class,
                category=category,
                title=rng.choice(INCIDENT_TITLES),
                description="Faits constatés par l'équipe éducative (données de démonstration).",
                incident_date=year.start_date + timedelta(days=rng.randint(20, 200)),
                severity=category.default_severity,
                status=rng.choice(
                    [
                        DisciplinaryIncident.Status.CONFIRMED,
                        DisciplinaryIncident.Status.CLOSED,
                        DisciplinaryIncident.Status.REVIEW,
                    ]
                ),
                reported_by=actor,
            )
            inc_count += 1

            if rng.random() < 0.55:
                ParentSummons.objects.create(
                    academic_year=year,
                    student=enrollment.student,
                    incident=incident,
                    summon_number=f"CONV-{year.start_date.year}-{idx + 1:04d}",
                    reason=rng.choice(SUMMONS_REASONS),
                    description="Convocation des responsables pour entretien.",
                    summon_date=incident.incident_date + timedelta(days=rng.randint(2, 10)),
                    summon_time=time(rng.randint(8, 15), rng.choice((0, 30))),
                    location="Bureau du préfet des études",
                    status=rng.choice(
                        [
                            ParentSummons.Status.SENT,
                            ParentSummons.Status.CONFIRMED,
                            ParentSummons.Status.PRESENT,
                            ParentSummons.Status.CLOSED,
                        ]
                    ),
                    created_by=actor,
                    delivery_mode=ParentSummons.DeliveryMode.MOBILE_APP,
                    delivery_date=timezone.now() - timedelta(days=rng.randint(1, 60)),
                )
                summ_count += 1

        return att_count, inc_count, summ_count

    def _school_days(self, year: AcademicYear, *, count: int, rng: random.Random) -> list[date]:
        days: list[date] = []
        cursor = year.start_date + timedelta(days=7)
        while cursor < year.end_date and len(days) < count:
            if cursor.weekday() < 5:
                days.append(cursor)
            cursor += timedelta(days=rng.randint(1, 3))
        return days[:count]
