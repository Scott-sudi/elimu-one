"""Student card models."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from .base import PublicIdModel
from .enrollment import Enrollment
from .student import Student


class StudentCard(PublicIdModel):
    """A generated student identification card."""

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="cards",
        verbose_name="Élève",
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="cards",
        verbose_name="Inscription",
    )
    qr_identifier = models.CharField(
        "Identifiant QR",
        max_length=255,
        unique=True,
    )
    card_number = models.CharField("Numéro de carte", max_length=50, unique=True)
    generated_at = models.DateTimeField("Générée le", auto_now_add=True)
    expires_at = models.DateTimeField("Expire le", null=True, blank=True)
    is_active = models.BooleanField("Active", default=True, db_index=True)
    is_blocked = models.BooleanField("Bloquée", default=False, db_index=True)
    block_reason = models.TextField("Motif du blocage", blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="generated_student_cards",
        null=True,
        blank=True,
        verbose_name="Générée par",
    )
    qr_image = models.ImageField(
        "Image du code QR",
        upload_to="students/cards/qr/%Y/",
        blank=True,
    )
    pdf_file = models.FileField(
        "Carte PDF",
        upload_to="students/cards/pdf/%Y/",
        blank=True,
    )
    updated_at = models.DateTimeField("Modifiée le", auto_now=True)

    class Meta:
        ordering = ["-generated_at"]
        verbose_name = "Carte d'élève"
        verbose_name_plural = "Cartes d'élèves"
        indexes = [
            models.Index(fields=["student", "is_active", "is_blocked"]),
            models.Index(fields=["enrollment", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.card_number} — {self.student}"

    def block(self, reason: str = "") -> None:
        self.is_blocked = True
        self.block_reason = reason
        self.save(update_fields=["is_blocked", "block_reason", "updated_at"])
