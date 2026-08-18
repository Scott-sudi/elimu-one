"""Management command: create initial administrator (rescue)."""

from getpass import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.services import AuthenticationError, create_initial_administrator, has_administrator


class Command(BaseCommand):
    help = "Crée le premier administrateur (assistant de secours, sans mot de passe codé en dur)."

    def add_arguments(self, parser):
        parser.add_argument("--nom", required=True)
        parser.add_argument("--prenom", required=True)
        parser.add_argument("--username", required=True)
        parser.add_argument("--postnom", default="")
        parser.add_argument("--telephone", default="")
        parser.add_argument("--email", default="")
        parser.add_argument(
            "--password",
            default="",
            help="Si omis, le mot de passe est demandé interactivement.",
        )

    def handle(self, *args, **options):
        if has_administrator():
            raise CommandError("Un administrateur existe déjà.")

        password = options.get("password") or ""
        if not password:
            password = getpass("Mot de passe : ")
            confirm = getpass("Confirmation : ")
            if password != confirm:
                raise CommandError("Les mots de passe ne correspondent pas.")
        if not password:
            raise CommandError("Le mot de passe est obligatoire.")

        try:
            user = create_initial_administrator(
                nom=options["nom"],
                postnom=options["postnom"],
                prenom=options["prenom"],
                telephone=options["telephone"],
                email=options["email"],
                username=options["username"],
                password=password,
            )
        except AuthenticationError as exc:
            raise CommandError(exc.message) from exc

        self.stdout.write(self.style.SUCCESS(f"Administrateur créé : {user.username}"))
