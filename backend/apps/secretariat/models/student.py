"""Student models."""

from __future__ import annotations

from django.db import models

from .base import TimeStampedPublicIdModel


class Student(TimeStampedPublicIdModel):
    """A student registered with the school."""

    class Gender(models.TextChoices):
        MALE = "M", "Masculin"
        FEMALE = "F", "Féminin"
        OTHER = "O", "Autre"

    class Status(models.TextChoices):
        ACTIVE = "ACTIF", "Actif"
        TRANSFERRED = "TRANSFERE", "Transféré"
        DROPPED_OUT = "ABANDON", "Abandon"
        GRADUATED = "DIPLOME", "Diplômé"
        SUSPENDED = "SUSPENDU", "Suspendu"
        ARCHIVED = "ARCHIVE", "Archivé"

    matricule = models.CharField("Matricule", max_length=50, unique=True)
    nom = models.CharField("Nom", max_length=100, db_index=True)
    postnom = models.CharField("Postnom", max_length=100, blank=True, db_index=True)
    prenom = models.CharField("Prénom", max_length=100, db_index=True)
    sexe = models.CharField("Sexe", max_length=1, choices=Gender.choices)
    date_naissance = models.DateField("Date de naissance")
    lieu_naissance = models.CharField("Lieu de naissance", max_length=150, blank=True)
    nationalite = models.CharField("Nationalité", max_length=100, blank=True)
    adresse = models.TextField("Adresse", blank=True)
    photo = models.ImageField(
        "Photo",
        upload_to="students/photos/%Y/",
        blank=True,
    )
    ancien_etablissement = models.CharField(
        "Ancien établissement",
        max_length=255,
        blank=True,
    )
    date_admission = models.DateField("Date d'admission")
    statut = models.CharField(
        "Statut",
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    is_active = models.BooleanField("Actif", default=True, db_index=True)
    is_archived = models.BooleanField("Archivé", default=False, db_index=True)
    groupe_sanguin = models.CharField("Groupe sanguin", max_length=5, blank=True)
    allergies = models.TextField("Allergies", blank=True)
    conditions_medicales = models.TextField("Conditions médicales", blank=True)
    observations = models.TextField("Observations", blank=True)

    class Meta:
        ordering = ["nom", "postnom", "prenom"]
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"
        indexes = [
            models.Index(fields=["nom", "postnom", "prenom"]),
            models.Index(fields=["statut", "is_active", "is_archived"]),
        ]

    def __str__(self) -> str:
        names = " ".join(part for part in (self.nom, self.postnom, self.prenom) if part)
        return f"{self.matricule} — {names}"

    def archive(self) -> None:
        self.statut = self.Status.ARCHIVED
        self.is_active = False
        self.is_archived = True
        self.save(
            update_fields=["statut", "is_active", "is_archived", "updated_at"],
        )

    def deactivate(self) -> None:
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])
