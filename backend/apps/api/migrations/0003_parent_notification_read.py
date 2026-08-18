from django.db import migrations, models
import django.db.models.deletion


def copy_attendance_receipts(apps, schema_editor):
    old_model = apps.get_model("api", "ParentAttendanceNoticeRead")
    new_model = apps.get_model("api", "ParentNotificationRead")
    for row in old_model.objects.select_related("attendance").iterator():
        receipt, created = new_model.objects.get_or_create(
            guardian_id=row.guardian_id,
            source="discipline_attendance",
            source_id=str(row.attendance.public_id),
        )
        # `auto_now_add` remplace la valeur à l'insertion ; restaurer l'instant
        # historique explicitement pour conserver la sémantique « relu si modifié ».
        if created:
            new_model.objects.filter(pk=receipt.pk).update(read_at=row.read_at)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0002_parent_attendance_notice_read"),
        ("secretariat", "0001_initial_secretariat"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParentNotificationRead",
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
                ("source", models.CharField(db_index=True, max_length=64)),
                ("source_id", models.CharField(max_length=64)),
                ("read_at", models.DateTimeField(auto_now_add=True)),
                (
                    "guardian",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_reads",
                        to="secretariat.guardian",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lecture notification parent",
                "verbose_name_plural": "Lectures notifications parents",
                "indexes": [
                    models.Index(
                        fields=["guardian", "source", "source_id"],
                        name="api_parentn_guardia_22479e_idx",
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="parentnotificationread",
            constraint=models.UniqueConstraint(
                fields=("guardian", "source", "source_id"),
                name="uniq_parent_notification_read",
            ),
        ),
        migrations.RunPython(copy_attendance_receipts, migrations.RunPython.noop),
    ]
