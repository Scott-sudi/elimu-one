"""Audit models for login attempts and action logs."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class LoginAttempt(models.Model):
    """Records successful and failed authentication attempts."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_attempts",
    )
    attempted_username = models.CharField(max_length=150)
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device = models.CharField(max_length=100, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    operating_system = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tentative de connexion"
        verbose_name_plural = "Tentatives de connexion"

    def __str__(self) -> str:
        status = "succès" if self.success else "échec"
        return f"{self.attempted_username} — {status}"


class AuditLog(models.Model):
    """Application action journal."""

    class Action(models.TextChoices):
        USER_CREATED = "user_created", "Création d'utilisateur"
        USER_UPDATED = "user_updated", "Modification d'utilisateur"
        ROLE_CHANGED = "role_changed", "Changement de rôle"
        USER_ACTIVATED = "user_activated", "Activation"
        USER_DEACTIVATED = "user_deactivated", "Désactivation"
        USER_ARCHIVED = "user_archived", "Archivage"
        PASSWORD_RESET = "password_reset", "Réinitialisation du mot de passe"
        LOGIN_SUCCESS = "login_success", "Connexion réussie"
        LOGIN_FAILED = "login_failed", "Connexion échouée"
        PROFILE_UPDATED = "profile_updated", "Modification du profil"
        PASSWORD_CHANGED = "password_changed", "Changement de mot de passe"
        LOGOUT = "logout", "Déconnexion"
        SETUP_COMPLETED = "setup_completed", "Configuration initiale"
        PERMISSION_TOGGLED = "permission_toggled", "Modification de permission"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions",
    )
    action = models.CharField(max_length=50, choices=Action.choices, db_index=True)
    entity_type = models.CharField(max_length=100, blank=True)
    entity_public_id = models.CharField(max_length=64, blank=True)
    description = models.TextField()
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journal d'activités"

    def __str__(self) -> str:
        return f"{self.action} — {self.created_at}"
