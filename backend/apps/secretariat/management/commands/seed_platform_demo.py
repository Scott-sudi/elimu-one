"""Peuple une démo ELIMU One : années récentes, classes, élèves (dont profils anglophones), cartes et présences."""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Données de démonstration pour la plateforme ELIMU One : "
        "2024-2025 → 2026-2027, niveaux, classes, élèves, cartes, présences, finance."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--students",
            type=int,
            default=90,
            help="Effectif cible pour l'année active (défaut: 90).",
        )
        parser.add_argument(
            "--skip-cards",
            action="store_true",
            help="Ne pas générer les cartes PNG/PDF.",
        )

    def handle(self, *args, **options):
        call_command(
            "seed_haut_katanga_demo",
            from_year=2024,
            to_year=2027,
            students=options["students"],
            foreign=12,
            english=10,
            cards_from="2026-2027",
            skip_cards=options["skip_cards"],
            skip_discipline=False,
            skip_finance=False,
            discipline_years=3,
            discipline_days=22,
        )
