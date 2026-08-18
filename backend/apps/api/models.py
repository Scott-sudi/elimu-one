from django.conf import settings
from django.db import models


class ParentPushDevice(models.Model):
    """Jeton appareil (FCM) pour notifications push parents."""

    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        WEB = "web", "Web"

    guardian = models.ForeignKey(
        "secretariat.Guardian",
        on_delete=models.CASCADE,
        related_name="push_devices",
        verbose_name="Responsable",
    )
    token = models.CharField("Jeton FCM", max_length=512, unique=True, db_index=True)
    platform = models.CharField(
        "Plateforme",
        max_length=16,
        choices=Platform.choices,
        default=Platform.ANDROID,
    )
    is_active = models.BooleanField("Actif", default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Appareil push parent"
        verbose_name_plural = "Appareils push parents"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.guardian_id} · {self.platform} · {self.token[:16]}…"


def fcm_server_key() -> str:
    return (getattr(settings, "FCM_SERVER_KEY", None) or "").strip()


class ParentAttendanceNoticeRead(models.Model):
    """Lecture parent d'une notif de présence (pointage)."""

    guardian = models.ForeignKey(
        "secretariat.Guardian",
        on_delete=models.CASCADE,
        related_name="attendance_notice_reads",
    )
    attendance = models.ForeignKey(
        "discipline.DailyAttendance",
        on_delete=models.CASCADE,
        related_name="parent_notice_reads",
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lecture notif présence"
        verbose_name_plural = "Lectures notifs présence"
        constraints = [
            models.UniqueConstraint(
                fields=["guardian", "attendance"],
                name="uniq_parent_attendance_notice_read",
            ),
        ]


class ParentNotificationRead(models.Model):
    """Persistent per-guardian receipt for any parent notification source."""

    guardian = models.ForeignKey(
        "secretariat.Guardian",
        on_delete=models.CASCADE,
        related_name="notification_reads",
    )
    source = models.CharField(max_length=64, db_index=True)
    source_id = models.CharField(max_length=64)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lecture notification parent"
        verbose_name_plural = "Lectures notifications parents"
        constraints = [
            models.UniqueConstraint(
                fields=["guardian", "source", "source_id"],
                name="uniq_parent_notification_read",
            ),
        ]
        indexes = [models.Index(fields=["guardian", "source", "source_id"])]
