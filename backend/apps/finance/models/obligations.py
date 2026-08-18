"""Student fee obligation models."""

from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .base import TimeStampedPublicIdModel
from .fees import SchoolFee


class StudentFeeObligation(TimeStampedPublicIdModel):
    """Amount a student enrollment owes for a given approved school fee."""

    class Status(models.TextChoices):
        UNPAID = "NON_PAYE", "Non payé"
        PARTIAL = "PARTIEL", "Partiel"
        PAID = "PAYE", "Payé"
        EXEMPTED = "EXONERE", "Exonéré"
        CANCELLED = "ANNULE", "Annulé"

    fee = models.ForeignKey(
        SchoolFee,
        on_delete=models.PROTECT,
        related_name="obligations",
        verbose_name="Frais",
    )
    enrollment = models.ForeignKey(
        "secretariat.Enrollment",
        on_delete=models.PROTECT,
        related_name="fee_obligations",
        verbose_name="Inscription",
    )
    student = models.ForeignKey(
        "secretariat.Student",
        on_delete=models.PROTECT,
        related_name="fee_obligations",
        verbose_name="Élève",
    )
    amount_due = models.DecimalField(
        "Montant dû",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount_paid = models.DecimalField(
        "Montant payé",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        "Statut",
        max_length=15,
        choices=Status.choices,
        default=Status.UNPAID,
        db_index=True,
    )

    class Meta:
        ordering = ["fee__label", "enrollment_id"]
        verbose_name = "Obligation de frais"
        verbose_name_plural = "Obligations de frais"
        constraints = [
            models.UniqueConstraint(
                fields=["fee", "enrollment"],
                name="finance_unique_obligation_fee_enrollment",
                violation_error_message=(
                    "Une obligation existe déjà pour ce frais et cette inscription."
                ),
            ),
        ]
        indexes = [
            models.Index(fields=["enrollment", "status"]),
            models.Index(fields=["student", "status"]),
            models.Index(fields=["fee", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.enrollment} — {self.fee.code} ({self.status})"

    @property
    def amount_remaining(self) -> Decimal:
        remaining = self.amount_due - self.amount_paid
        return remaining if remaining > 0 else Decimal("0.00")

    @property
    def payment_tone(self) -> str:
        """CSS tone: unpaid (red), partial (orange), paid (green)."""
        if self.status == self.Status.PARTIAL:
            return "partial"
        if self.status in {self.Status.PAID, self.Status.EXEMPTED}:
            return "paid"
        return "unpaid"
