from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("secretariat", "0002_communication_pin_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="academicyear",
            name="closure_notes",
            field=models.TextField(
                blank=True,
                help_text="Bilan ou observations enregistrées lors de la déclaration de fin d'année.",
                verbose_name="Observation de clôture",
            ),
        ),
    ]
