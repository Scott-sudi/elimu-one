"""Custom user and role models for Kalunga school staff."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class Role(models.Model):
    """System role assigned to staff accounts."""

    CODE_ADMINISTRATEUR = "ADMINISTRATEUR"
    CODE_SECRETAIRE = "SECRETAIRE"
    CODE_COMPTABLE = "COMPTABLE"
    CODE_DISCIPLINE = "DISCIPLINE"

    SYSTEM_ROLES = (
        (CODE_ADMINISTRATEUR, "Administrateur"),
        (CODE_SECRETAIRE, "Secrétaire"),
        (CODE_COMPTABLE, "Comptable"),
        (CODE_DISCIPLINE, "Discipline"),
    )

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"

    def __str__(self) -> str:
        return self.name

    @property
    def is_administrateur(self) -> bool:
        return self.code == self.CODE_ADMINISTRATEUR


class UserManager(BaseUserManager):
    """Manager for the custom User model."""

    use_in_migrations = True

    def _create_user(self, username: str, password: str | None, **extra_fields):
        if not username:
            raise ValueError("Le nom d'utilisateur est obligatoire.")
        email = extra_fields.pop("email", None)
        if email:
            email = self.normalize_email(email)
        user = self.model(username=username, email=email or "", **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Le superutilisateur doit avoir is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Le superutilisateur doit avoir is_superuser=True.")
        return self._create_user(username, password, **extra_fields)


class User(AbstractUser):
    """Staff user for the Kalunga school management system."""

    class Gender(models.TextChoices):
        MALE = "M", "Masculin"
        FEMALE = "F", "Féminin"
        OTHER = "O", "Autre"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    nom = models.CharField(max_length=100)
    postnom = models.CharField(max_length=100, blank=True)
    prenom = models.CharField(max_length=100)
    sexe = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    telephone = models.CharField(max_length=30, blank=True)
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )
    is_archived = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    # Prefer our naming; keep AbstractUser first_name/last_name unused
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    objects = UserManager()

    REQUIRED_FIELDS = ["nom", "prenom"]

    class Meta:
        ordering = ["nom", "prenom"]
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        permissions = [
            ("view_admin_dashboard", "Peut consulter le tableau de bord administrateur"),
            ("manage_users", "Peut gérer les utilisateurs"),
            ("view_login_history", "Peut consulter l'historique des connexions"),
            ("view_audit_log", "Peut consulter le journal d'activités"),
            ("manage_own_profile", "Peut gérer son propre profil"),
        ]

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    def get_full_name(self) -> str:
        parts = [self.nom, self.postnom, self.prenom]
        return " ".join(p for p in parts if p).strip()

    def get_short_name(self) -> str:
        return self.prenom or self.username

    @property
    def initials(self) -> str:
        first = (self.prenom or self.username or "?")[:1].upper()
        last = (self.nom or "")[:1].upper()
        return f"{first}{last}"

    @property
    def role_code(self) -> str:
        return self.role.code if self.role_id else ""

    @property
    def role_name(self) -> str:
        return self.role.name if self.role_id else ""

    def is_administrateur(self) -> bool:
        return bool(self.role_id and self.role.code == Role.CODE_ADMINISTRATEUR)

    def is_locked(self) -> bool:
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def can_authenticate(self) -> bool:
        return self.is_active and not self.is_archived and not self.is_locked()

    def archive(self) -> None:
        self.is_archived = True
        self.is_active = False
        self.archived_at = timezone.now()
        self.save(update_fields=["is_archived", "is_active", "archived_at", "updated_at"])

    def deactivate(self) -> None:
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    def activate(self) -> None:
        self.is_active = True
        self.is_archived = False
        self.archived_at = None
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(
            update_fields=[
                "is_active",
                "is_archived",
                "archived_at",
                "failed_login_attempts",
                "locked_until",
                "updated_at",
            ]
        )

    def reset_failed_attempts(self) -> None:
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=["failed_login_attempts", "locked_until", "updated_at"])

    def register_failed_attempt(self, max_attempts: int, lockout_minutes: int) -> None:
        self.failed_login_attempts += 1
        update_fields = ["failed_login_attempts", "updated_at"]
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timedelta(minutes=lockout_minutes)
            update_fields.append("locked_until")
        self.save(update_fields=update_fields)


class SystemConfiguration(models.Model):
    """Tracks whether initial setup has been completed."""

    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    SETUP_COMPLETE_KEY = "setup_complete"

    class Meta:
        verbose_name = "Configuration système"
        verbose_name_plural = "Configurations système"

    def __str__(self) -> str:
        return self.key

    @classmethod
    def is_setup_complete(cls) -> bool:
        return cls.objects.filter(key=cls.SETUP_COMPLETE_KEY, value="true").exists()

    @classmethod
    def mark_setup_complete(cls) -> None:
        cls.objects.update_or_create(
            key=cls.SETUP_COMPLETE_KEY,
            defaults={"value": "true"},
        )
