"""Management command: verify MySQL / database readiness."""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Vérifie la connexion MySQL et l'état de la base kalunga_school."

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        self.stdout.write(f"Moteur : {db.get('ENGINE')}")
        self.stdout.write(f"Base : {db.get('NAME')} @ {db.get('HOST')}:{db.get('PORT')}")

        try:
            connection.ensure_connection()
        except Exception as exc:
            self.stderr.write(
                self.style.ERROR(
                    "Impossible de se connecter à MySQL. Vérifiez que WampServer est démarré "
                    "et que le service MySQL est actif."
                )
            )
            self.stderr.write(str(exc))
            return

        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()[0]
            cursor.execute(
                "SELECT DEFAULT_CHARACTER_SET_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                [db.get("NAME")],
            )
            row = cursor.fetchone()
            charset = row[0] if row else "inconnu"

        self.stdout.write(self.style.SUCCESS(f"MySQL répond (version {version})."))
        self.stdout.write(f"Base active : {current_db}")
        self.stdout.write(f"Jeu de caractères : {charset}")

        if charset and "utf8" not in charset.lower():
            self.stdout.write(
                self.style.WARNING("Le jeu de caractères n'est pas utf8/utf8mb4. Vérifiez la configuration.")
            )

        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            self.stdout.write(
                self.style.WARNING(f"{len(plan)} migration(s) en attente. Exécutez : python manage.py migrate")
            )
        else:
            self.stdout.write(self.style.SUCCESS("Toutes les migrations sont appliquées."))
