"""Envoie un push FCM de test à un parent (vérifie app fermée).

Usage:
  python manage.py send_test_parent_push --phone +243...
  python manage.py send_test_parent_push --guardian-public-id <uuid>
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.api.models import ParentPushDevice
from apps.api.parents_push import send_push_to_guardians
from apps.secretariat.models import Guardian


class Command(BaseCommand):
    help = "Envoie une notification push FCM de test à un parent."

    def add_arguments(self, parser):
        parser.add_argument("--phone", default="", help="Téléphone parent")
        parser.add_argument(
            "--guardian-public-id",
            default="",
            help="UUID public du guardian",
        )
        parser.add_argument(
            "--title",
            default="Test ELIMU Go",
        )
        parser.add_argument(
            "--body",
            default="Si tu vois ceci app fermée, le push FCM fonctionne.",
        )

    def handle(self, *args, **options):
        phone = (options.get("phone") or "").strip()
        gpid = (options.get("guardian_public_id") or "").strip()
        qs = Guardian.objects.filter(is_active=True, is_archived=False)
        if gpid:
            guardian = qs.filter(public_id=gpid).first()
        elif phone:
            digits = "".join(c for c in phone if c.isdigit())
            guardian = None
            for g in qs.iterator():
                gdigits = "".join(c for c in (g.phone or "") if c.isdigit())
                if gdigits.endswith(digits[-9:]) or digits.endswith(gdigits[-9:]):
                    guardian = g
                    break
        else:
            raise CommandError("Indique --phone ou --guardian-public-id")

        if guardian is None:
            raise CommandError("Parent introuvable.")

        devices = ParentPushDevice.objects.filter(
            guardian=guardian, is_active=True
        ).exclude(token__startswith="local-")
        count = devices.count()
        self.stdout.write(
            f"Parent={guardian} public_id={guardian.public_id} devices_actifs={count}"
        )
        if count == 0:
            raise CommandError(
                "Aucun jeton FCM enregistré. Ouvre l’app parents (APK récent), "
                "connecte-toi, puis réessaie."
            )

        sent = send_push_to_guardians(
            guardians=[guardian],
            title=options["title"],
            body=options["body"],
            data={"type": "test_push", "source_id": "manual-test"},
        )
        self.stdout.write(self.style.SUCCESS(f"Envois FCM OK: {sent}/{count}"))
