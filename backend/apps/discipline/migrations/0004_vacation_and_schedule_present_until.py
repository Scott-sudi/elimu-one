# Generated manually for Horaires de présence (vacation + present_until)

from datetime import datetime, timedelta

from django.db import migrations, models


def backfill_present_until(apps, schema_editor):
    AttendanceSchedule = apps.get_model("discipline", "AttendanceSchedule")
    to_update = []
    for schedule in AttendanceSchedule.objects.all().only(
        "id", "start_time", "tolerance_minutes", "present_until"
    ):
        if schedule.present_until or not schedule.start_time:
            continue
        base = datetime.combine(datetime.min.date(), schedule.start_time)
        schedule.present_until = (
            base + timedelta(minutes=int(schedule.tolerance_minutes or 0))
        ).time()
        to_update.append(schedule)
    if to_update:
        AttendanceSchedule.objects.bulk_update(to_update, ["present_until"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("secretariat", "0005_schoolclass_vacation"),
        ("discipline", "0003_class_attendance_sheet_and_records"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendanceschedule",
            name="vacation",
            field=models.CharField(
                blank=True,
                choices=[("AVANT_MIDI", "Avant-midi"), ("APRES_MIDI", "Après-midi")],
                db_index=True,
                help_text=(
                    "Avant-midi ou après-midi "
                    "(horaire général pour les classes de cette vacation)."
                ),
                max_length=12,
                verbose_name="Vacation",
            ),
        ),
        migrations.AddField(
            model_name="attendanceschedule",
            name="present_until",
            field=models.TimeField(
                blank=True,
                help_text="Fin de tolérance : après cette heure, l'élève est en retard.",
                null=True,
                verbose_name="Présent jusqu'à",
            ),
        ),
        migrations.AlterField(
            model_name="attendanceschedule",
            name="start_time",
            field=models.TimeField(verbose_name="Début des cours"),
        ),
        migrations.AlterField(
            model_name="attendanceschedule",
            name="end_time",
            field=models.TimeField(blank=True, null=True, verbose_name="Fin des cours"),
        ),
        migrations.AlterModelOptions(
            name="attendanceschedule",
            options={
                "ordering": [
                    "academic_year",
                    "vacation",
                    "school_class__name",
                    "level__order",
                    "label",
                ],
                "verbose_name": "Horaire de pointage",
                "verbose_name_plural": "Horaires de pointage",
            },
        ),
        migrations.RunPython(backfill_present_until, noop_reverse),
    ]
