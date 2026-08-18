"""Payment, allocation and receipt sequence models."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .base import TimeStampedPublicIdModel
from .obligations import StudentFeeObligation


class Payment(TimeStampedPublicIdModel):
    """A recorded payment against one or more fee obligations."""

    class PaymentMethod(models.TextChoices):
        CASH = "ESPECES", "Espèces"
        MOBILE_MONEY = "MOBILE_MONEY", "Mobile money"
        TRANSFER = "VIREMENT", "Virement"
        DEPOSIT = "DEPOT", "Dépôt"
        CARD = "CARTE", "Carte"
        OTHER = "AUTRE", "Autre"

    class Status(models.TextChoices):
        VALID = "VALIDE", "Validé"
        CANCELLED = "ANNULE", "Annulé"

    academic_year = models.ForeignKey(
        "secretariat.AcademicYear",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Année scolaire",
    )
    enrollment = models.ForeignKey(
        "secretariat.Enrollment",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Inscription",
    )
    student = models.ForeignKey(
        "secretariat.Student",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Élève",
    )
    receipt_number = models.CharField(
        "Numéro de reçu",
        max_length=50,
        unique=True,
    )
    payment_date = models.DateField("Date de paiement", db_index=True)
    amount_total = models.DecimalField(
        "Montant total",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField("Devise", max_length=10, default="CDF")
    payment_method = models.CharField(
        "Mode de paiement",
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    transaction_reference = models.CharField(
        "Référence de transaction",
        max_length=100,
        blank=True,
    )
    payer_name = models.CharField("Nom du payeur", max_length=200, blank=True)
    payer_phone = models.CharField("Téléphone du payeur", max_length=30, blank=True)
    observation = models.TextField("Observation", blank=True)
    status = models.CharField(
        "Statut",
        max_length=15,
        choices=Status.choices,
        default=Status.VALID,
        db_index=True,
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="recorded_payments",
        null=True,
        blank=True,
        verbose_name="Enregistré par",
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="cancelled_payments",
        null=True,
        blank=True,
        verbose_name="Annulé par",
    )
    cancelled_at = models.DateTimeField("Annulé le", null=True, blank=True)
    cancellation_reason = models.TextField("Motif d'annulation", blank=True)

    class Meta:
        ordering = ["-payment_date", "-created_at"]
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        indexes = [
            models.Index(fields=["academic_year", "status"]),
            models.Index(fields=["enrollment", "status"]),
            models.Index(fields=["student", "payment_date"]),
            models.Index(fields=["payment_date", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.receipt_number} — {self.amount_total} {self.currency}"

    @property
    def list_tone(self) -> str:
        """
        Green when allocated obligations are settled, orange when still partial.
        Cancelled payments have no payment tone.
        """
        if self.status == self.Status.CANCELLED:
            return ""
        tones = {
            allocation.obligation.payment_tone
            for allocation in self.allocations.all()
        }
        if not tones:
            return "partial"
        if "partial" in tones or "unpaid" in tones:
            return "partial"
        return "paid"


class PaymentAllocation(TimeStampedPublicIdModel):
    """Portion of a payment applied to a single obligation."""

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="allocations",
        verbose_name="Paiement",
    )
    obligation = models.ForeignKey(
        StudentFeeObligation,
        on_delete=models.PROTECT,
        related_name="allocations",
        verbose_name="Obligation",
    )
    amount = models.DecimalField(
        "Montant",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        ordering = ["payment_id", "id"]
        verbose_name = "Allocation de paiement"
        verbose_name_plural = "Allocations de paiement"
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "obligation"],
                name="finance_unique_allocation_payment_obligation",
            ),
        ]
        indexes = [
            models.Index(fields=["obligation", "payment"]),
        ]

    def __str__(self) -> str:
        return f"{self.payment.receipt_number} → {self.obligation_id}: {self.amount}"


class ReceiptSequence(TimeStampedPublicIdModel):
    """Per-year counter used to generate unique receipt numbers."""

    academic_year = models.OneToOneField(
        "secretariat.AcademicYear",
        on_delete=models.PROTECT,
        related_name="receipt_sequence",
        verbose_name="Année scolaire",
    )
    last_value = models.PositiveIntegerField("Dernière valeur", default=0)

    class Meta:
        verbose_name = "Séquence de reçu"
        verbose_name_plural = "Séquences de reçus"

    def __str__(self) -> str:
        return f"{self.academic_year} — {self.last_value}"
