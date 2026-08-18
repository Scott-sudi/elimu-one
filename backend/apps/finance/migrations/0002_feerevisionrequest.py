# Generated manually for FeeRevisionRequest (prepared, UI inactive).

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0001_finance_module_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FeeRevisionRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "public_id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Créé le"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Modifié le"),
                ),
                (
                    "requested_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=14,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                        verbose_name="Montant proposé",
                    ),
                ),
                ("reason", models.TextField(verbose_name="Motif")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("BROUILLON", "Brouillon"),
                            ("EN_ATTENTE", "En attente"),
                            ("APPROUVE", "Approuvé"),
                            ("REJETE", "Rejeté"),
                            ("ANNULE", "Annulé"),
                        ],
                        db_index=True,
                        default="BROUILLON",
                        max_length=15,
                        verbose_name="Statut",
                    ),
                ),
                (
                    "reviewed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Revu le"
                    ),
                ),
                (
                    "review_comment",
                    models.TextField(blank=True, verbose_name="Commentaire de revue"),
                ),
                (
                    "fee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="revision_requests",
                        to="finance.schoolfee",
                        verbose_name="Frais",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="fee_revision_requests",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Demandé par",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_fee_revisions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Revu par",
                    ),
                ),
            ],
            options={
                "verbose_name": "Demande de révision de frais",
                "verbose_name_plural": "Demandes de révision de frais",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["fee", "status"],
                        name="finance_fee_fee_id_7f2a1a_idx",
                    ),
                    models.Index(
                        fields=["status", "created_at"],
                        name="finance_fee_status_9c4b2d_idx",
                    ),
                ],
            },
        ),
    ]
