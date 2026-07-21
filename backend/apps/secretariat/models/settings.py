"""Secretariat key/value settings."""

from __future__ import annotations

from django.db import models

from .base import TimeStampedPublicIdModel


class SecretariatSetting(TimeStampedPublicIdModel):
    """A configurable secretariat value, such as a matricule format."""

    key = models.CharField("Clé", max_length=100, unique=True)
    value = models.TextField("Valeur", blank=True)
    description = models.TextField("Description", blank=True)
    is_active = models.BooleanField("Actif", default=True, db_index=True)

    class Meta:
        ordering = ["key"]
        verbose_name = "Paramètre du secrétariat"
        verbose_name_plural = "Paramètres du secrétariat"

    def __str__(self) -> str:
        return self.key
