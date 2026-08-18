# Generated for ParentAttendanceNoticeRead

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_parent_push_device"),
        ("discipline", "0002_discipline_workflows"),
        ("secretariat", "0001_initial_secretariat"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParentAttendanceNoticeRead",
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
                ("read_at", models.DateTimeField(auto_now_add=True)),
                (
                    "attendance",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parent_notice_reads",
                        to="discipline.dailyattendance",
                    ),
                ),
                (
                    "guardian",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendance_notice_reads",
                        to="secretariat.guardian",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lecture notif présence",
                "verbose_name_plural": "Lectures notifs présence",
            },
        ),
        migrations.AddConstraint(
            model_name="parentattendancenoticeread",
            constraint=models.UniqueConstraint(
                fields=("guardian", "attendance"),
                name="uniq_parent_attendance_notice_read",
            ),
        ),
    ]
