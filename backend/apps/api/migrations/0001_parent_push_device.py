# Generated manually for ParentPushDevice

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("secretariat", "0001_initial_secretariat"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParentPushDevice",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "token",
                    models.CharField(
                        db_index=True,
                        max_length=512,
                        unique=True,
                        verbose_name="Jeton FCM",
                    ),
                ),
                (
                    "platform",
                    models.CharField(
                        choices=[
                            ("android", "Android"),
                            ("ios", "iOS"),
                            ("web", "Web"),
                        ],
                        default="android",
                        max_length=16,
                        verbose_name="Plateforme",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True, default=True, verbose_name="Actif"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "guardian",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="push_devices",
                        to="secretariat.guardian",
                        verbose_name="Responsable",
                    ),
                ),
            ],
            options={
                "verbose_name": "Appareil push parent",
                "verbose_name_plural": "Appareils push parents",
                "ordering": ["-updated_at"],
            },
        ),
    ]
