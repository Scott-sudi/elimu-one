# Generated manually for fee schedule / grouping fields.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0002_feerevisionrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolfee",
            name="schedule_mode",
            field=models.CharField(
                choices=[
                    ("UNE_FOIS", "Une seule fois"),
                    ("TRANCHES", "Par tranche"),
                    ("MOIS", "Par mois"),
                ],
                db_index=True,
                default="UNE_FOIS",
                max_length=15,
                verbose_name="Mode de paiement",
            ),
        ),
        migrations.AddField(
            model_name="schoolfee",
            name="group_key",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Clé commune pour regrouper les colonnes d'un même frais (tranches / mois).",
                max_length=40,
                verbose_name="Groupe de frais",
            ),
        ),
        migrations.AddField(
            model_name="schoolfee",
            name="period_index",
            field=models.PositiveSmallIntegerField(
                db_index=True,
                default=0,
                help_text="Ordre de la colonne dans le groupe (tranche ou mois).",
                verbose_name="Index de période",
            ),
        ),
    ]
