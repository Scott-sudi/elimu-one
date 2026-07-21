"""Student document models."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from .academic import SchoolLevel
from .base import TimeStampedPublicIdModel
from .student import Student


class DocumentType(TimeStampedPublicIdModel):
    """A type of document accepted by the secretariat."""

    name = models.CharField("Nom", max_length=150, db_index=True)
    code = models.CharField("Code", max_length=50, unique=True)
    is_required = models.BooleanField("Obligatoire", default=False, db_index=True)
    level = models.ForeignKey(
        SchoolLevel,
        on_delete=models.PROTECT,
        related_name="document_types",
        null=True,
        blank=True,
        verbose_name="Niveau",
    )
    description = models.TextField("Description", blank=True)
    is_active = models.BooleanField("Actif", default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Type de document"
        verbose_name_plural = "Types de documents"

    def __str__(self) -> str:
        return self.name


class StudentDocument(TimeStampedPublicIdModel):
    """A document received for a student."""

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "En attente"
        VALIDATED = "VALIDATED", "Validé"
        REJECTED = "REJECTED", "Rejeté"

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="documents",
        verbose_name="Élève",
    )
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="student_documents",
        verbose_name="Type de document",
    )
    file = models.FileField(
        "Fichier",
        upload_to="students/documents/%Y/%m/",
    )
    verification_status = models.CharField(
        "Statut de vérification",
        max_length=10,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )
    received_at = models.DateTimeField("Reçu le")
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="verified_student_documents",
        null=True,
        blank=True,
        verbose_name="Vérifié par",
    )
    observation = models.TextField("Observation", blank=True)

    class Meta:
        ordering = ["-received_at"]
        verbose_name = "Document d'élève"
        verbose_name_plural = "Documents d'élèves"
        indexes = [
            models.Index(fields=["student", "verification_status"]),
            models.Index(fields=["document_type", "verification_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} — {self.document_type}"
