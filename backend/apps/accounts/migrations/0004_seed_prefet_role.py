# Generated manually for PREFET role seed

from django.db import migrations


def seed_prefet_role(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.get_or_create(
        code="PREFET",
        defaults={
            "name": "Préfet",
            "description": (
                "Responsable chargé de la consultation des tableaux de bord décisionnels "
                "et des indicateurs de gestion de l'établissement."
            ),
            "is_system": True,
            "is_active": True,
        },
    )


def noop_reverse(apps, schema_editor):
    # Keep system role; do not delete on reverse.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_user_profile_photo"),
    ]

    operations = [
        migrations.RunPython(seed_prefet_role, noop_reverse),
    ]
