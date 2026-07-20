"""Audit logging services."""

from __future__ import annotations

from typing import Any

from apps.audit.models import AuditLog, LoginAttempt
from apps.core.utils import get_client_ip, parse_user_agent


SENSITIVE_KEYS = {
    "password",
    "password1",
    "password2",
    "old_password",
    "new_password",
    "confirm_password",
    "temporary_password",
    "token",
    "access",
    "refresh",
    "secret",
}


def sanitize_values(values: dict | None) -> dict:
    if not values:
        return {}
    cleaned = {}
    for key, value in values.items():
        if key.lower() in SENSITIVE_KEYS or "password" in key.lower() or "token" in key.lower():
            continue
        cleaned[key] = value
    return cleaned


def record_login_attempt(
    *,
    request,
    attempted_username: str,
    success: bool,
    user=None,
    failure_reason: str = "",
) -> LoginAttempt:
    ua = request.META.get("HTTP_USER_AGENT", "")
    parsed = parse_user_agent(ua)
    return LoginAttempt.objects.create(
        user=user,
        attempted_username=attempted_username,
        success=success,
        failure_reason=failure_reason,
        ip_address=get_client_ip(request),
        user_agent=ua[:1000],
        device=parsed["device"],
        browser=parsed["browser"],
        operating_system=parsed["operating_system"],
    )


def log_action(
    *,
    request=None,
    actor=None,
    action: str,
    description: str,
    entity_type: str = "",
    entity_public_id: str = "",
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> AuditLog:
    ip = get_client_ip(request) if request is not None else None
    if actor is None and request is not None and getattr(request, "user", None):
        user = request.user
        if user.is_authenticated:
            actor = user
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_public_id=str(entity_public_id) if entity_public_id else "",
        description=description,
        old_values=sanitize_values(old_values),
        new_values=sanitize_values(new_values),
        ip_address=ip,
    )


def user_snapshot(user) -> dict[str, Any]:
    return {
        "public_id": str(user.public_id),
        "username": user.username,
        "nom": user.nom,
        "postnom": user.postnom,
        "prenom": user.prenom,
        "email": user.email,
        "telephone": user.telephone,
        "sexe": user.sexe,
        "role": user.role_code,
        "is_active": user.is_active,
        "is_archived": user.is_archived,
        "must_change_password": user.must_change_password,
    }
