"""Seed full history 2009-2027 — wrapper around cohort engine.

Use this command if seed_haut_katanga_demo was not yet updated locally.
"""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Alias vers seed_haut_katanga_demo (historique 2009-2027)."

    def add_arguments(self, parser):
        parser.add_argument("--skip-cards", action="store_true")
        parser.add_argument("--skip-discipline", action="store_true")
        parser.add_argument("--skip-finance", action="store_true")
        parser.add_argument("--students", type=int, default=220)
        parser.add_argument("--foreign", type=int, default=6)
        parser.add_argument("--cards-from", type=str, default="2022-2023")

    def handle(self, *args, **options):
        call_command(
            "seed_haut_katanga_demo",
            students=options["students"],
            foreign=options["foreign"],
            skip_cards=options["skip_cards"],
            skip_discipline=options["skip_discipline"],
            skip_finance=options["skip_finance"],
            cards_from=options["cards_from"],
        )
