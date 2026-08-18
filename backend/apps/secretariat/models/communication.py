"""School communication models."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from .academic import AcademicYear, Option, SchoolClass, SchoolLevel, Section
from .base import TimeStampedPublicIdModel
from .guardian import Guardian
from .student import Student


class Communication(TimeStampedPublicIdModel):
    """A notice published by the school."""

    class Category(models.TextChoices):
        GENERAL = "GENERALE", "Générale"
        ACADEMIC = "ACADEMIQUE", "Académique"
        ADMINISTRATIVE = "ADMINISTRATIVE", "Administrative"
        EVENT = "EVENEMENT", "Événement"
        EMERGENCY = "URGENCE", "Urgence"

    class Priority(models.TextChoices):
        NORMAL = "NORMALE", "Normale"
        IMPORTANT = "IMPORTANTE", "Importante"
        URGENT = "URGENTE", "Urgente"

    class Status(models.TextChoices):
        DRAFT = "BROUILLON", "Brouillon"
        SCHEDULED = "PROGRAMMEE", "Programmée"
        PUBLISHED = "PUBLIEE", "Publiée"
        EXPIRED = "EXPIREE", "Expirée"
        ARCHIVED = "ARCHIVEE", "Archivée"

    title = models.CharField("Titre", max_length=255, db_index=True)
    content = models.TextField("Contenu")
    category = models.CharField(
        "Catégorie",
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
        db_index=True,
    )
    priority = models.CharField(
        "Priorité",
        max_length=15,
        choices=Priority.choices,
        default=Priority.NORMAL,
        db_index=True,
    )
    status = models.CharField(
        "Statut",
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField("Publiée le", null=True, blank=True)
    expires_at = models.DateTimeField("Expire le", null=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="communications",
        null=True,
        blank=True,
        verbose_name="Auteur",
    )
    attachment = models.FileField(
        "Pièce jointe",
        upload_to="communications/attachments/%Y/%m/",
        blank=True,
    )
    is_pinned = models.BooleanField("Épinglée", default=False, db_index=True)
    pinned_at = models.DateTimeField("Épinglée le", null=True, blank=True)
    pinned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="pinned_communications",
        null=True,
        blank=True,
        db_constraint=False,
        verbose_name="Épinglée par",
    )

    class Meta:
        ordering = ["-is_pinned", "-published_at", "-created_at"]
        verbose_name = "Communication"
        verbose_name_plural = "Communications"
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["category", "priority"]),
            models.Index(fields=["is_pinned", "pinned_at"]),
        ]

    def __str__(self) -> str:
        return self.title


class CommunicationTarget(models.Model):
    """A recipient scope for a communication."""

    class TargetType(models.TextChoices):
        ALL_PARENTS = "ALL_PARENTS", "Tous les parents"
        ACADEMIC_YEAR = "ACADEMIC_YEAR", "Année scolaire"
        LEVEL = "LEVEL", "Niveau"
        SECTION = "SECTION", "Section"
        OPTION = "OPTION", "Option"
        CLASS = "CLASS", "Classe"
        STUDENT = "STUDENT", "Élève"
        GUARDIAN = "GUARDIAN", "Responsable"

    communication = models.ForeignKey(
        Communication,
        on_delete=models.CASCADE,
        related_name="targets",
        verbose_name="Communication",
    )
    target_type = models.CharField(
        "Type de cible",
        max_length=20,
        choices=TargetType.choices,
        db_index=True,
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="communication_targets",
        null=True,
        blank=True,
        verbose_name="Année scolaire",
    )
    level = models.ForeignKey(
        SchoolLevel,
        on_delete=models.CASCADE,
        related_name="communication_targets",
        null=True,
        blank=True,
        verbose_name="Niveau",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="communication_targets",
        null=True,
        blank=True,
        verbose_name="Section",
    )
    option = models.ForeignKey(
        Option,
        on_delete=models.CASCADE,
        related_name="communication_targets",
        null=True,
        blank=True,
        verbose_name="Option",
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="communication_targets",
        null=True,
        blank=True,
        verbose_name="Classe",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="communication_targets",
        null=True,
        blank=True,
        verbose_name="Élève",
    )
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name="communication_targets",
        null=True,
        blank=True,
        verbose_name="Responsable",
    )

    class Meta:
        ordering = ["communication", "target_type"]
        verbose_name = "Cible de communication"
        verbose_name_plural = "Cibles de communication"
        indexes = [
            models.Index(fields=["communication", "target_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.communication} — {self.get_target_type_display()}"


class CommunicationReceipt(models.Model):
    """Delivery/read state for a real guardian communication receipt."""

    communication = models.ForeignKey(
        Communication,
        on_delete=models.CASCADE,
        related_name="receipts",
        verbose_name="Communication",
    )
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name="communication_receipts",
        verbose_name="Responsable",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="communication_receipts",
        null=True,
        blank=True,
        verbose_name="Élève",
    )
    read_at = models.DateTimeField("Lu le", null=True, blank=True)
    created_at = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Accusé de communication"
        verbose_name_plural = "Accusés de communication"
        indexes = [
            models.Index(fields=["guardian", "read_at"]),
            models.Index(fields=["communication", "guardian"]),
        ]

    def __str__(self) -> str:
        return f"{self.communication} — {self.guardian}"
