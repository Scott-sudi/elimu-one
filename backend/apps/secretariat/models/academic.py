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
    name = models.CharField("Nom", max_length=100, db_index=True)
    code = models.CharField("Code", max_length=30, db_index=True)
    max_capacity = models.PositiveIntegerField("Capacité maximale")
    room = models.CharField("Local", max_length=100, blank=True)
    description = models.TextField("Description", blank=True)
    is_active = models.BooleanField("Active", default=True, db_index=True)

    class Meta:
        ordering = ["academic_year", "level__order", "name"]
        verbose_name = "Classe"
        verbose_name_plural = "Classes"
        constraints = [
            models.UniqueConstraint(
                fields=["code", "academic_year"],
                name="secretariat_unique_class_code_per_year",
            ),
            models.CheckConstraint(
                condition=Q(max_capacity__gt=0),
                name="secretariat_school_class_positive_capacity",
            ),
        ]
        indexes = [
            models.Index(fields=["academic_year", "is_active"]),
            models.Index(fields=["level", "section", "option"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.academic_year})"
