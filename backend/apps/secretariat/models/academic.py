"""Academic structure models."""

from __future__ import annotations

from django.db import models
from django.db.models import F, Q

from .base import TimeStampedPublicIdModel


class AcademicYear(TimeStampedPublicIdModel):
    """A school academic year."""

    label = models.CharField("Libellé", max_length=50, unique=True)
    start_date = models.DateField("Date de début")
    end_date = models.DateField("Date de fin")
    is_active = models.BooleanField("Active", default=False, db_index=True)
    is_closed = models.BooleanField("Clôturée", default=False, db_index=True)
    closure_notes = models.TextField(
        "Observation de clôture",
        blank=True,
        help_text="Bilan ou observations enregistrées lors de la déclaration de fin d'année.",
    )

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Année scolaire"
        verbose_name_plural = "Années scolaires"
        constraints = [
            models.CheckConstraint(
                condition=Q(start_date__lt=F("end_date")),
                name="secretariat_academic_year_dates_order",
            ),
        ]

    def __str__(self) -> str:
        return self.label


class SchoolLevel(TimeStampedPublicIdModel):
    """A level in the school's curriculum."""

    name = models.CharField("Nom", max_length=100, db_index=True)
    code = models.CharField(
        "Code",
        max_length=30,
        unique=True,
        null=True,
        blank=True,
    )
    order = models.PositiveSmallIntegerField("Ordre", default=0, db_index=True)
    description = models.TextField("Description", blank=True)
    is_active = models.BooleanField("Actif", default=True, db_index=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Niveau scolaire"
        verbose_name_plural = "Niveaux scolaires"

    def __str__(self) -> str:
        return self.name


class Section(TimeStampedPublicIdModel):
    """A school section."""

    name = models.CharField("Nom", max_length=100, db_index=True)
    code = models.CharField("Code", max_length=30, unique=True)
    description = models.TextField("Description", blank=True)
    is_active = models.BooleanField("Active", default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Section"
        verbose_name_plural = "Sections"

    def __str__(self) -> str:
        return self.name


class Option(TimeStampedPublicIdModel):
    """An academic option, optionally attached to a section."""

    name = models.CharField("Nom", max_length=100, db_index=True)
    code = models.CharField("Code", max_length=30, unique=True)
    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="options",
        null=True,
        blank=True,
        verbose_name="Section",
    )
    description = models.TextField("Description", blank=True)
    is_active = models.BooleanField("Active", default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Option"
        verbose_name_plural = "Options"

    def __str__(self) -> str:
        return self.name


class SchoolClass(TimeStampedPublicIdModel):
    """A class opened for an academic year."""

    LETTER_CHOICES = tuple((letter, letter) for letter in "ABCDEFGH")

    class Vacation(models.TextChoices):
        MORNING = "AVANT_MIDI", "Avant-midi"
        AFTERNOON = "APRES_MIDI", "Après-midi"

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="school_classes",
        verbose_name="Année scolaire",
    )
    level = models.ForeignKey(
        SchoolLevel,
        on_delete=models.PROTECT,
        related_name="school_classes",
        verbose_name="Niveau",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="school_classes",
        null=True,
        blank=True,
        verbose_name="Section",
    )
    option = models.ForeignKey(
        Option,
        on_delete=models.PROTECT,
        related_name="school_classes",
        null=True,
        blank=True,
        verbose_name="Option",
    )
    letter = models.CharField(
        "Lettre",
        max_length=1,
        choices=LETTER_CHOICES,
        blank=True,
        db_index=True,
        help_text="Lettre de la classe (A, B, C, D…).",
    )
    name = models.CharField("Nom", max_length=100, db_index=True)
    code = models.CharField("Code", max_length=30, db_index=True)
    max_capacity = models.PositiveIntegerField("Capacité maximale")
    room = models.CharField("Local", max_length=100, blank=True)
    description = models.TextField("Description", blank=True)
    vacation = models.CharField(
        "Vacation",
        max_length=12,
        choices=Vacation.choices,
        default=Vacation.MORNING,
        db_index=True,
        help_text="Avant-midi ou après-midi — détermine l'horaire de pointage applicable.",
    )
    is_active = models.BooleanField("Active", default=True, db_index=True)

    class Meta:
        ordering = ["academic_year", "level__order", "name"]
        verbose_name = "Classe"
        verbose_name_plural = "Classes"
        constraints = [
            models.UniqueConstraint(
                fields=["code", "academic_year"],
                name="secretariat_unique_class_code_per_year",
                violation_error_message=(
                    "Une classe avec ce code existe déjà pour cette année scolaire."
                ),
            ),
            models.UniqueConstraint(
                fields=["name", "academic_year"],
                name="secretariat_unique_class_name_per_year",
                violation_error_message=(
                    "Une classe avec ce nom existe déjà pour cette année scolaire."
                ),
            ),
            models.CheckConstraint(
                condition=Q(max_capacity__gt=0),
                name="secretariat_school_class_positive_capacity",
            ),
        ]
        indexes = [
            models.Index(fields=["academic_year", "is_active"]),
            models.Index(fields=["level", "section", "option"]),
            models.Index(fields=["academic_year", "level", "letter"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.academic_year})"

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        errors = {}

        if self.code:
            self.code = self.code.strip()
        if self.name:
            self.name = self.name.strip()
        if self.letter:
            self.letter = self.letter.strip().upper()

        year_id = self.academic_year_id
        if not year_id:
            return

        if self.code:
            code_qs = SchoolClass.objects.filter(
                academic_year_id=year_id,
                code__iexact=self.code,
            )
            if self.pk:
                code_qs = code_qs.exclude(pk=self.pk)
            if code_qs.exists():
                errors["code"] = (
                    f"Une classe avec le code « {self.code} » existe déjà "
                    "pour cette année scolaire."
                )

        if self.name:
            name_qs = SchoolClass.objects.filter(
                academic_year_id=year_id,
                name__iexact=self.name,
            )
            if self.pk:
                name_qs = name_qs.exclude(pk=self.pk)
            if name_qs.exists():
                errors["name"] = (
                    f"Une classe avec le nom « {self.name} » existe déjà "
                    "pour cette année scolaire."
                )

        if self.letter and self.level_id:
            letter_qs = SchoolClass.objects.filter(
                academic_year_id=year_id,
                level_id=self.level_id,
                letter=self.letter,
                section_id=self.section_id,
                option_id=self.option_id,
            )
            if self.pk:
                letter_qs = letter_qs.exclude(pk=self.pk)
            if letter_qs.exists():
                level_label = str(self.level) if self.level_id else "ce niveau"
                scope = level_label
                if self.section_id:
                    scope = f"{scope} / {self.section}"
                if self.option_id:
                    scope = f"{scope} / {self.option}"
                errors["letter"] = (
                    f"Impossible : une classe « {scope} {self.letter} » existe déjà. "
                    "Deux classes ne peuvent pas avoir la même lettre "
                    "pour le même niveau (section/option)."
                )

        if errors:
            raise ValidationError(errors)
