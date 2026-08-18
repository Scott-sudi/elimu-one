"""Shared abstract models for the finance application."""

from __future__ import annotations

import uuid

from django.db import models


class PublicIdModel(models.Model):
    """Add a stable public UUID to a model."""

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    class Meta:
        abstract = True


class TimeStampedPublicIdModel(PublicIdModel):
    """Add a public UUID and creation/update timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    class Meta:
        abstract = True
