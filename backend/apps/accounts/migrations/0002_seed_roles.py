"""Data migration: seed system roles."""

from django.db import migrations


ROLES = [
    (
        "ADMINISTRATEUR",
        "Administrateur",
        "Gestion complète des comptes du personnel et de la configuration système.",
    ),
    (
        "SECRETAIRE",
        "Secrétaire",
        "Accès futur au module secrétariat (inscriptions, élèves, parents).",
    ),
    (
        "COMPTABLE",
        "Comptable",
        "Accès futur au module comptabilité (frais et paiements).",
    ),
    (
        "DISCIPLINE",
        "Discipline",
        "Accès futur au module discipline (présences, incidents).",
    ),
]


def create_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for code, name, description in ROLES:
        Role.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "description": description,
                "is_system": True,
                "is_active": True,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_roles, noop),
    ]
