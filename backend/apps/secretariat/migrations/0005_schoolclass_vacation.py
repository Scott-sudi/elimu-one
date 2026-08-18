# Generated manually for Horaires de présence (vacation AM/PM)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("secretariat", "0004_school_class_letter_and_unique_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolclass",
            name="vacation",
            field=models.CharField(
                choices=[("AVANT_MIDI", "Avant-midi"), ("APRES_MIDI", "Après-midi")],
                db_index=True,
                default="AVANT_MIDI",
                help_text="Avant-midi ou après-midi — détermine l'horaire de pointage applicable.",
                max_length=12,
                verbose_name="Vacation",
            ),
        ),
    ]
