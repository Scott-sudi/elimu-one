"""Authentication and account services."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, SystemConfiguration, User
from apps.audit.models import AuditLog
from apps.audit.services import log_action, record_login_attempt, user_snapshot


class AuthenticationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def has_administrator() -> bool:
    return User.objects.filter(
        role__code=Role.CODE_ADMINISTRATEUR,
        is_archived=False,
    ).exists()


def ensure_system_roles() -> dict[str, Role]:
    descriptions = {
        Role.CODE_ADMINISTRATEUR: "Gestion complète des comptes du personnel et de la configuration système.",
        Role.CODE_SECRETAIRE: "Accès au module secrétariat (inscriptions, élèves, parents).",
        Role.CODE_COMPTABLE: "Accès au module comptabilité (frais et paiements).",
        Role.CODE_DISCIPLINE: "Accès au module discipline (présences, incidents).",
        Role.CODE_PREFET: (
            "Responsable chargé de la consultation des tableaux de bord décisionnels "
            "et des indicateurs de gestion de l'établissement."
        ),
    }
    roles = {}
    for code, name in Role.SYSTEM_ROLES:
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "description": descriptions.get(code, ""),
                "is_system": True,
                "is_active": True,
            },
        )
        roles[code] = role
    return roles


@transaction.atomic
def create_initial_administrator(
    *,
    nom: str,
    postnom: str,
    prenom: str,
    telephone: str,
    email: str,
    username: str,
    password: str,
    request=None,
) -> User:
    if has_administrator() or SystemConfiguration.is_setup_complete():
        raise AuthenticationError("La configuration initiale a déjà été effectuée.")

    roles = ensure_system_roles()
    admin_role = roles[Role.CODE_ADMINISTRATEUR]
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email or "",
        nom=nom,
        postnom=postnom or "",
        prenom=prenom,
        telephone=telephone or "",
        role=admin_role,
        is_staff=True,
        is_superuser=True,
        is_active=True,
        must_change_password=False,
    )
    SystemConfiguration.mark_setup_complete()
    log_action(
        request=request,
        actor=user,
        action=AuditLog.Action.SETUP_COMPLETED,
        description="Configuration initiale terminée. Premier administrateur créé.",
        entity_type="User",
        entity_public_id=str(user.public_id),
        new_values=user_snapshot(user),
    )
    return user


def authenticate_user(*, request, username: str, password: str) -> User:
    username = (username or "").strip()
    if not username or not password:
        raise AuthenticationError("Identifiants incorrects.")

    existing = User.objects.filter(username__iexact=username).select_related("role").first()
    if existing and existing.is_locked():
        record_login_attempt(
            request=request,
            attempted_username=username,
            success=False,
            user=existing,
            failure_reason="Compte temporairement verrouillé",
        )
        log_action(
            request=request,
            actor=existing,
            action=AuditLog.Action.LOGIN_FAILED,
            description=f"Tentative de connexion sur un compte verrouillé ({username}).",
            entity_type="User",
            entity_public_id=str(existing.public_id),
        )
        raise AuthenticationError(
            "Impossible de se connecter. Vérifiez vos identifiants ou réessayez plus tard."
        )

    if existing and existing.is_archived:
        record_login_attempt(
            request=request,
            attempted_username=username,
            success=False,
            user=existing,
            failure_reason="Compte archivé",
        )
        raise AuthenticationError("Impossible de se connecter. Vérifiez vos identifiants.")

    if existing and not existing.is_active:
        record_login_attempt(
            request=request,
            attempted_username=username,
            success=False,
            user=existing,
            failure_reason="Compte désactivé",
        )
        raise AuthenticationError("Impossible de se connecter. Vérifiez vos identifiants.")

    user = authenticate(request, username=username, password=password)
    if user is None:
        if existing:
            existing.register_failed_attempt(
                settings.MAX_FAILED_LOGIN_ATTEMPTS,
                settings.ACCOUNT_LOCKOUT_MINUTES,
            )
        record_login_attempt(
            request=request,
            attempted_username=username,
            success=False,
            user=existing,
            failure_reason="Identifiants incorrects",
        )
        log_action(
            request=request,
            actor=existing,
            action=AuditLog.Action.LOGIN_FAILED,
            description=f"Échec de connexion pour {username}.",
            entity_type="User",
            entity_public_id=str(existing.public_id) if existing else "",
        )
        raise AuthenticationError("Identifiants incorrects.")

    user.reset_failed_attempts()
    login(request, user)
    record_login_attempt(
        request=request,
        attempted_username=username,
        success=True,
        user=user,
    )
    log_action(
        request=request,
        actor=user,
        action=AuditLog.Action.LOGIN_SUCCESS,
        description=f"Connexion réussie de {user.get_full_name()}.",
        entity_type="User",
        entity_public_id=str(user.public_id),
    )
    return user


def logout_user(*, request) -> None:
    user = request.user if request.user.is_authenticated else None
    if user:
        log_action(
            request=request,
            actor=user,
            action=AuditLog.Action.LOGOUT,
            description=f"Déconnexion de {user.get_full_name()}.",
            entity_type="User",
            entity_public_id=str(user.public_id),
        )
    logout(request)


@transaction.atomic
def create_staff_user(*, request, data: dict) -> User:
    role = Role.objects.get(pk=data["role_id"])
    if User.objects.filter(username__iexact=data["username"]).exists():
        raise AuthenticationError("Le nom d'utilisateur existe déjà.")

    user = User.objects.create_user(
        username=data["username"],
        password=data["password"],
        email=data.get("email") or "",
        nom=data["nom"],
        postnom=data.get("postnom") or "",
        prenom=data["prenom"],
        sexe=data.get("sexe") or "",
        telephone=data.get("telephone") or "",
        role=role,
        is_active=data.get("is_active", True),
        must_change_password=data.get("must_change_password", True),
        is_staff=role.code == Role.CODE_ADMINISTRATEUR,
        is_superuser=role.code == Role.CODE_ADMINISTRATEUR,
    )
    log_action(
        request=request,
        action=AuditLog.Action.USER_CREATED,
        description=f"Utilisateur créé : {user.get_full_name()} ({user.username}).",
        entity_type="User",
        entity_public_id=str(user.public_id),
        new_values=user_snapshot(user),
    )
    return user


@transaction.atomic
def update_staff_user(*, request, user: User, data: dict) -> User:
    old = user_snapshot(user)
    role_changed = False
    if "role_id" in data and data["role_id"]:
        new_role = Role.objects.get(pk=data["role_id"])
        if user.role_id != new_role.id:
            role_changed = True
            user.role = new_role
            user.is_staff = new_role.code == Role.CODE_ADMINISTRATEUR
            user.is_superuser = new_role.code == Role.CODE_ADMINISTRATEUR

    for field in ("nom", "postnom", "prenom", "sexe", "telephone", "email", "username"):
        if field in data and data[field] is not None:
            setattr(user, field, data[field])

    if "is_active" in data and data["is_active"] is not None:
        user.is_active = bool(data["is_active"])
    if "must_change_password" in data and data["must_change_password"] is not None:
        user.must_change_password = bool(data["must_change_password"])

    if (
        "username" in data
        and User.objects.filter(username__iexact=data["username"]).exclude(pk=user.pk).exists()
    ):
        raise AuthenticationError("Le nom d'utilisateur existe déjà.")

    user.save()
    new = user_snapshot(user)
    log_action(
        request=request,
        action=AuditLog.Action.USER_UPDATED,
        description=f"Utilisateur modifié : {user.get_full_name()}.",
        entity_type="User",
        entity_public_id=str(user.public_id),
        old_values=old,
        new_values=new,
    )
    if role_changed:
        log_action(
            request=request,
            action=AuditLog.Action.ROLE_CHANGED,
            description=f"Rôle modifié pour {user.get_full_name()} → {user.role_name}.",
            entity_type="User",
            entity_public_id=str(user.public_id),
            old_values={"role": old.get("role")},
            new_values={"role": new.get("role")},
        )
    return user


def set_user_status(*, request, user: User, action: str) -> User:
    old = user_snapshot(user)
    if action == "activate":
        user.activate()
        audit_action = AuditLog.Action.USER_ACTIVATED
        description = f"Compte réactivé : {user.get_full_name()}."
    elif action == "deactivate":
        user.deactivate()
        audit_action = AuditLog.Action.USER_DEACTIVATED
        description = f"Compte désactivé : {user.get_full_name()}."
    elif action == "archive":
        user.archive()
        audit_action = AuditLog.Action.USER_ARCHIVED
        description = f"Compte archivé : {user.get_full_name()}."
    else:
        raise AuthenticationError("Action de statut invalide.")

    log_action(
        request=request,
        action=audit_action,
        description=description,
        entity_type="User",
        entity_public_id=str(user.public_id),
        old_values=old,
        new_values=user_snapshot(user),
    )
    return user


def reset_user_password(*, request, user: User, temporary_password: str, force_change: bool = True) -> User:
    user.set_password(temporary_password)
    user.must_change_password = force_change
    user.failed_login_attempts = 0
    user.locked_until = None
    user.save(
        update_fields=[
            "password",
            "must_change_password",
            "failed_login_attempts",
            "locked_until",
            "updated_at",
        ]
    )
    log_action(
        request=request,
        action=AuditLog.Action.PASSWORD_RESET,
        description=f"Mot de passe temporaire réinitialisé pour {user.get_full_name()}.",
        entity_type="User",
        entity_public_id=str(user.public_id),
    )
    return user


def change_own_password(*, request, user: User, old_password: str, new_password: str) -> User:
    if not user.check_password(old_password):
        raise AuthenticationError("L'ancien mot de passe est incorrect.")
    user.set_password(new_password)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password", "updated_at"])
    # Keep the current session valid after the password change,
    # otherwise the user is silently logged out.
    update_session_auth_hash(request, user)
    log_action(
        request=request,
        actor=user,
        action=AuditLog.Action.PASSWORD_CHANGED,
        description="Mot de passe personnel modifié.",
        entity_type="User",
        entity_public_id=str(user.public_id),
    )
    return user


def update_own_profile(
    *,
    request,
    user: User,
    nom: str,
    postnom: str,
    prenom: str,
    telephone: str,
    email: str,
    profile_photo=None,
) -> User:
    old = user_snapshot(user)
    user.nom = nom.strip()
    user.postnom = postnom.strip()
    user.prenom = prenom.strip()
    user.telephone = telephone or ""
    user.email = email or ""
    update_fields = ["nom", "postnom", "prenom", "telephone", "email", "updated_at"]
    if profile_photo:
        user.profile_photo = profile_photo
        update_fields.append("profile_photo")
    user.save(update_fields=update_fields)
    log_action(
        request=request,
        actor=user,
        action=AuditLog.Action.PROFILE_UPDATED,
        description="Profil personnel modifié.",
        entity_type="User",
        entity_public_id=str(user.public_id),
        old_values=old,
        new_values=user_snapshot(user),
    )
    return user
