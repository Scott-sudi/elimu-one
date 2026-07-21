"""Enrollment and class transfer models."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from .academic import AcademicYear, SchoolClass
from .base import PublicIdModel, TimeStampedPublicIdModel
from .student import Student


class Enrollment(TimeStampedPublicIdModel):
    """A student's enrollment for an academic year."""

    class EnrollmentType(models.TextChoices):
        NEW = "NOUVELLE_INSCRIPTION", "Nouvelle inscription"
        RENEWAL = "REINSCRIPTION", "Réinscription"
        INCOMING_TRANSFER = "TRANSFERT_ENTRANT", "Transfert entrant"

    class Status(models.TextChoices):
        DRAFT = "BROUILLON", "Brouillon"
        VALIDATED = "VALIDEE", "Validée"
        CANCELLED = "ANNULEE", "Annulée"
        CLOSED = "CLOTUREE", "Clôturée"

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="Élève",
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="Année scolaire",
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="Classe",
    )
    enrollment_number = models.CharField(
        "Numéro d'inscription",
        max_length=50,
        unique=True,
    )
    enrollment_type = models.CharField(
        "Type d'inscription",
        max_length=30,
        choices=EnrollmentType.choices,
    )
    enrollment_date = models.DateField("Date d'inscription")
    status = models.CharField(
        "Statut",
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    provenance = models.CharField("Provenance", max_length=255, blank=True)
    observation = models.TextField("Observation", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_enrollments",
        null=True,
        blank=True,
        verbose_name="Créée par",
    )

    class Meta:
        ordering = ["-enrollment_date", "-created_at"]
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        # Unicité d'une inscription VALIDEE par année : contrôlée en service
        # (MySQL ne gère pas correctement UniqueConstraint conditionnelle).
        constraints = []
        indexes = [
            models.Index(fields=["academic_year", "status"]),
            models.Index(fields=["school_class", "status"]),
            models.Index(fields=["student", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.enrollment_number} — {self.student}"


class ClassTransfer(PublicIdModel):
    """A trace of a student's transfer between classes."""

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="class_transfers",
        verbose_name="Élève",
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="class_transfers",
        verbose_name="Inscription",
    )
    from_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
        verbose_name="Classe d'origine",
    )
    to_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        verbose_name="Classe de destination",
    )
    motif = models.TextField("Motif")
    transfer_date = models.DateField("Date du transfert", db_index=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="performed_class_transfers",
        null=True,
        blank=True,
        verbose_name="Effectué par",
    )
    created_at = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        ordering = ["-transfer_date", "-created_at"]
        verbose_name = "Transfert de classe"
        verbose_name_plural = "Transferts de classe"
        indexes = [
            models.Index(fields=["student", "transfer_date"]),
            models.Index(fields=["enrollment", "transfer_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.student}: {self.from_class} → {self.to_class}"
