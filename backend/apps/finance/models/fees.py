"""Fee catalogue, targeting and approval history models."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .base import TimeStampedPublicIdModel


class FeeCategory(TimeStampedPublicIdModel):
    """A category grouping school fees (scolarité, examens, etc.)."""

    code = models.CharField("Code", max_length=30, unique=True)
    name = models.CharField("Nom", max_length=100, db_index=True)
    description = models.TextField("Description", blank=True)
    order = models.PositiveSmallIntegerField("Ordre", default=0, db_index=True)
    is_active = models.BooleanField("Active", default=True, db_index=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Catégorie de frais"
        verbose_name_plural = "Catégories de frais"

    def __str__(self) -> str:
        return self.name


class SchoolFee(TimeStampedPublicIdModel):
    """A school fee defined for an academic year."""

    class ApplicationType(models.TextChoices):
        ALL_CLASSES = "TOUTES_LES_CLASSES", "Toutes les classes"
        SELECTED_CLASSES = "CLASSES_SELECTIONNEES", "Classes sélectionnées"
        LEVEL = "NIVEAU", "Niveau"
        SECTION = "SECTION", "Section"
        OPTION = "OPTION", "Option"

    class Status(models.TextChoices):
        DRAFT = "BROUILLON", "Brouillon"
        PENDING = "EN_ATTENTE", "En attente"
        APPROVED = "APPROUVE", "Approuvé"
        REJECTED = "REJETE", "Rejeté"
        CANCELLED = "ANNULE", "Annulé"
        ARCHIVED = "ARCHIVE", "Archivé"

    class ScheduleMode(models.TextChoices):
        ONCE = "UNE_FOIS", "Une seule fois"
        TRANCHES = "TRANCHES", "Par tranche"
        MONTHS = "MOIS", "Par mois"

    academic_year = models.ForeignKey(
        "secretariat.AcademicYear",
        on_delete=models.PROTECT,
        related_name="school_fees",
        verbose_name="Année scolaire",
    )
    category = models.ForeignKey(
        FeeCategory,
        on_delete=models.PROTECT,
        related_name="fees",
        verbose_name="Catégorie",
    )
    code = models.CharField("Code", max_length=30, db_index=True)
    label = models.CharField("Libellé", max_length=200)
    description = models.TextField("Description", blank=True)
    amount = models.DecimalField(
        "Montant",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField("Devise", max_length=10, default="CDF")
    due_date = models.DateField("Date d'échéance", null=True, blank=True)
    is_mandatory = models.BooleanField("Obligatoire", default=True)
    allow_partial = models.BooleanField("Paiement partiel autorisé", default=True)
    application_type = models.CharField(
        "Type d'application",
        max_length=30,
        choices=ApplicationType.choices,
        default=ApplicationType.ALL_CLASSES,
    )
    schedule_mode = models.CharField(
        "Mode de paiement",
        max_length=15,
        choices=ScheduleMode.choices,
        default=ScheduleMode.ONCE,
        db_index=True,
    )
    group_key = models.CharField(
        "Groupe de frais",
        max_length=40,
        blank=True,
        db_index=True,
        help_text="Clé commune pour regrouper les colonnes d'un même frais (tranches / mois).",
    )
    period_index = models.PositiveSmallIntegerField(
        "Index de période",
        default=0,
        db_index=True,
        help_text="Ordre de la colonne dans le groupe (tranche ou mois).",
    )
    status = models.CharField(
        "Statut",
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_school_fees",
        null=True,
        blank=True,
        verbose_name="Créé par",
    )
    submitted_at = models.DateTimeField("Soumis le", null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_school_fees",
        null=True,
        blank=True,
        verbose_name="Revue par",
    )
    reviewed_at = models.DateTimeField("Revu le", null=True, blank=True)
    rejection_reason = models.TextField("Motif de rejet", blank=True)
    is_active = models.BooleanField("Actif", default=True, db_index=True)
    is_archived = models.BooleanField("Archivé", default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Frais scolaire"
        verbose_name_plural = "Frais scolaires"
        constraints = [
            models.UniqueConstraint(
                fields=["code", "academic_year"],
                name="finance_unique_fee_code_per_year",
                violation_error_message=(
                    "Un frais avec ce code existe déjà pour cette année scolaire."
                ),
            ),
        ]
        indexes = [
            models.Index(fields=["academic_year", "status"]),
            models.Index(fields=["academic_year", "is_active", "is_archived"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.label}"


class FeeTarget(TimeStampedPublicIdModel):
    """A targeting rule attaching a fee to classes, levels, sections or options."""

    fee = models.ForeignKey(
        SchoolFee,
        on_delete=models.CASCADE,
        related_name="targets",
        verbose_name="Frais",
    )
    school_class = models.ForeignKey(
        "secretariat.SchoolClass",
        on_delete=models.PROTECT,
        related_name="fee_targets",
        null=True,
        blank=True,
        verbose_name="Classe",
    )
    level = models.ForeignKey(
        "secretariat.SchoolLevel",
        on_delete=models.PROTECT,
        related_name="fee_targets",
        null=True,
        blank=True,
        verbose_name="Niveau",
    )
    section = models.ForeignKey(
        "secretariat.Section",
        on_delete=models.PROTECT,
        related_name="fee_targets",
        null=True,
        blank=True,
        verbose_name="Section",
    )
    option = models.ForeignKey(
        "secretariat.Option",
        on_delete=models.PROTECT,
        related_name="fee_targets",
        null=True,
        blank=True,
        verbose_name="Option",
    )

    class Meta:
        ordering = ["fee", "id"]
        verbose_name = "Cible de frais"
        verbose_name_plural = "Cibles de frais"
        indexes = [
            models.Index(fields=["fee", "school_class"]),
            models.Index(fields=["fee", "level"]),
            models.Index(fields=["fee", "section"]),
            models.Index(fields=["fee", "option"]),
        ]

    def __str__(self) -> str:
        target = (
            self.school_class
            or self.level
            or self.section
            or self.option
            or "—"
        )
        return f"{self.fee.code} → {target}"


class FeeApprovalHistory(TimeStampedPublicIdModel):
    """Audit trail of fee workflow decisions."""

    class Action(models.TextChoices):
        CREATED = "CREATED", "Création"
        UPDATED = "UPDATED", "Modification"
        SUBMITTED = "SUBMITTED", "Soumission"
        WITHDRAWN = "WITHDRAWN", "Retrait"
        APPROVED = "APPROVED", "Approbation"
        REJECTED = "REJECTED", "Rejet"
        ARCHIVED = "ARCHIVED", "Archivage"
        CANCELLED = "CANCELLED", "Annulation"

    fee = models.ForeignKey(
        SchoolFee,
        on_delete=models.CASCADE,
        related_name="approval_history",
        verbose_name="Frais",
    )
    action = models.CharField("Action", max_length=20, choices=Action.choices)
    previous_status = models.CharField("Statut précédent", max_length=15, blank=True)
    new_status = models.CharField("Nouveau statut", max_length=15, blank=True)
    comment = models.TextField("Commentaire", blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="fee_approval_actions",
        null=True,
        blank=True,
        verbose_name="Acteur",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Historique d'approbation"
        verbose_name_plural = "Historiques d'approbation"
        indexes = [
            models.Index(fields=["fee", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.fee.code} — {self.action}"


class FeeRevisionRequest(TimeStampedPublicIdModel):
    """Prepared revision request for an approved fee (UI not activated yet)."""

    class Status(models.TextChoices):
        DRAFT = "BROUILLON", "Brouillon"
        PENDING = "EN_ATTENTE", "En attente"
        APPROVED = "APPROUVE", "Approuvé"
        REJECTED = "REJETE", "Rejeté"
        CANCELLED = "ANNULE", "Annulé"

    fee = models.ForeignKey(
        SchoolFee,
        on_delete=models.CASCADE,
        related_name="revision_requests",
        verbose_name="Frais",
    )
    requested_amount = models.DecimalField(
        "Montant proposé",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    reason = models.TextField("Motif")
    status = models.CharField(
        "Statut",
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="fee_revision_requests",
        null=True,
        blank=True,
        verbose_name="Demandé par",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_fee_revisions",
        null=True,
        blank=True,
        verbose_name="Revu par",
    )
    reviewed_at = models.DateTimeField("Revu le", null=True, blank=True)
    review_comment = models.TextField("Commentaire de revue", blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demande de révision de frais"
        verbose_name_plural = "Demandes de révision de frais"
        indexes = [
            models.Index(fields=["fee", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Révision {self.fee.code} ({self.status})"


class FeeClassAmount(TimeStampedPublicIdModel):
    """Per-class amount override for an approved fee period."""

    fee = models.ForeignKey(
        SchoolFee,
        on_delete=models.CASCADE,
        related_name="class_amounts",
        verbose_name="Frais",
    )
    school_class = models.ForeignKey(
        "secretariat.SchoolClass",
        on_delete=models.CASCADE,
        related_name="fee_amounts",
        verbose_name="Classe",
    )
    amount = models.DecimalField(
        "Montant",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        ordering = ["fee", "school_class__name"]
        verbose_name = "Montant de frais par classe"
        verbose_name_plural = "Montants de frais par classe"
        constraints = [
            models.UniqueConstraint(
                fields=["fee", "school_class"],
                name="finance_feeclassamount_fee_class_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["fee", "school_class"]),
        ]

    def __str__(self) -> str:
        return f"{self.fee.code} / {self.school_class} = {self.amount}"


class FeeAmountChangeRequest(TimeStampedPublicIdModel):
    """Pending change of a fee period amount (column header edit)."""

    class Scope(models.TextChoices):
        CURRENT_CLASS = "CETTE_CLASSE", "Cette classe uniquement"
        SELECTED_CLASSES = "CLASSES_SELECTIONNEES", "Classes spécifiques"
        ALL_CLASSES = "TOUTES_LES_CLASSES", "Toutes les classes"

    class Status(models.TextChoices):
        PENDING = "EN_ATTENTE", "En attente"
        APPROVED = "APPROUVE", "Approuvé"
        REJECTED = "REJETE", "Rejeté"
        CANCELLED = "ANNULE", "Annulé"

    fee = models.ForeignKey(
        SchoolFee,
        on_delete=models.CASCADE,
        related_name="amount_change_requests",
        verbose_name="Frais",
    )
    new_amount = models.DecimalField(
        "Nouveau montant",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    previous_base_amount = models.DecimalField(
        "Montant de base précédent",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    scope = models.CharField(
        "Portée",
        max_length=30,
        choices=Scope.choices,
        default=Scope.CURRENT_CLASS,
    )
    origin_class = models.ForeignKey(
        "secretariat.SchoolClass",
        on_delete=models.PROTECT,
        related_name="originated_fee_amount_changes",
        verbose_name="Classe d'origine",
    )
    target_classes = models.ManyToManyField(
        "secretariat.SchoolClass",
        related_name="fee_amount_change_requests",
        blank=True,
        verbose_name="Classes cibles",
    )
    status = models.CharField(
        "Statut",
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    comment = models.TextField("Commentaire", blank=True)
    rejection_reason = models.TextField("Motif de rejet", blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="fee_amount_change_requests",
        null=True,
        blank=True,
        verbose_name="Demandé par",
    )
    submitted_at = models.DateTimeField("Soumis le", null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_fee_amount_changes",
        null=True,
        blank=True,
        verbose_name="Revu par",
    )
    reviewed_at = models.DateTimeField("Revu le", null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at", "-created_at"]
        verbose_name = "Demande de modification de montant"
        verbose_name_plural = "Demandes de modification de montant"
        indexes = [
            models.Index(fields=["status", "submitted_at"]),
            models.Index(fields=["fee", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.fee.code} → {self.new_amount} ({self.get_status_display()})"
