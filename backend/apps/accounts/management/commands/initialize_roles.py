"""Management command: initialize system roles."""

from django.core.management.base import BaseCommand

from apps.accounts.services import ensure_system_roles


class Command(BaseCommand):
    help = "Crée ou met à jour les rôles système Kalunga."

    def handle(self, *args, **options):
        roles = ensure_system_roles()
        for code, role in roles.items():
            self.stdout.write(self.style.SUCCESS(f"Rôle prêt : {role.name} ({code})"))
