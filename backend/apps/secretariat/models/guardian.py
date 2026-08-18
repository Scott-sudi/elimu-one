"""Guardian and student/guardian relationship models."""

from __future__ import annotations

from django.db import models

from .base import TimeStampedPublicIdModel
from .student import Student


class Guardian(TimeStampedPublicIdModel):
    """A parent, guardian, or other responsible adult."""

    class Gender(models.TextChoices):
        MALE = "M", "Masculin"
        FEMALE = "F", "Féminin"
        OTHER = "O", "Autre"

    nom = models.CharField("Nom", max_length=100, db_index=True)
    postnom = models.CharField("Postnom", max_length=100, blank=True, db_index=True)
    prenom = models.CharField("Prénom", max_length=100, db_index=True)
    sexe = models.CharField(
        "Sexe",
        max_length=1,
        choices=Gender.choices,
        blank=True,
    )
    telephone_principal = models.CharField(
        "Téléphone principal",
        max_length=30,
        db_index=True,
    )
    telephone_secondaire = models.CharField(
        "Téléphone secondaire",
        max_length=30,
        blank=True,
    )
    email = models.EmailField("Adresse e-mail", blank=True, db_index=True)
    adresse = models.TextField("Adresse", blank=True)
    profession = models.CharField("Profession", max_length=150, blank=True)
    numero_identification = models.CharField(
        "Numéro d'identification",
        max_length=100,
        blank=True,
        db_index=True,
    )
    is_active = models.BooleanField("Actif", default=True, db_index=True)
    is_archived = models.BooleanField("Archivé", default=False, db_index=True)

    class Meta:
        ordering = ["nom", "postnom", "prenom"]
        verbose_name = "Responsable"
        verbose_name_plural = "Responsables"
        indexes = [
            models.Index(fields=["nom", "postnom", "prenom"]),
            models.Index(fields=["is_active", "is_archived"]),
        ]

    def __str__(self) -> str:
        return " ".join(
            part for part in (self.nom, self.postnom, self.prenom) if part
        )

    def archive(self) -> None:
        self.is_active = False
        self.is_archived = True
        self.save(update_fields=["is_active", "is_archived", "updated_at"])

    def restore(self) -> None:
        self.is_active = True
        self.is_archived = False
        self.save(update_fields=["is_active", "is_archived", "updated_at"])


class StudentGuardian(models.Model):
    """The relationship and permissions between a student and guardian.

    The application service must ensure that a student has no more than one
    primary guardian because MySQL does not provide portable partial indexes.
    """

    class Relationship(models.TextChoices):
        FATHER = "PERE", "Père"
        MOTHER = "MERE", "Mère"
        LEGAL_GUARDIAN = "TUTEUR", "Tuteur légal"
        BROTHER = "FRERE", "Frère"
        SISTER = "SOEUR", "Sœur"
        UNCLE = "ONCLE", "Oncle"
        AUNT = "TANTE", "Tante"
        GRANDPARENT = "GRAND_PARENT", "Grand-parent"
        OTHER = "AUTRE", "Autre"

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="guardian_links",
        verbose_name="Élève",
    )
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name="student_links",
        verbose_name="Responsable",
    )
    lien_parente = models.CharField(
        "Lien de parenté",
        max_length=20,
        choices=Relationship.choices,
    )
    is_primary = models.BooleanField("Responsable principal", default=False)
    is_emergency_contact = models.BooleanField("Contact d'urgence", default=False)
    can_pickup = models.BooleanField("Autorisé à récupérer l'élève", default=True)
    receives_notifications = models.BooleanField(
        "Reçoit les notifications",
        default=True,
    )
    lives_with_student = models.BooleanField("Vit avec l'élève", default=False)
    observation = models.TextField("Observation", blank=True)
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Modifié le", auto_now=True)

    class Meta:
        ordering = ["student", "-is_primary", "guardian"]
        verbose_name = "Responsable d'élève"
        verbose_name_plural = "Responsables d'élèves"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "guardian"],
                name="secretariat_unique_student_guardian",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "is_primary"]),
            models.Index(fields=["guardian", "receives_notifications"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} — {self.guardian} ({self.get_lien_parente_display()})"
