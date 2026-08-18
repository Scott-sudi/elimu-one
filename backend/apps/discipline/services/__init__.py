"""Business services for discipline application."""

from __future__ import annotations

from typing import Any

from apps.audit.services import log_action


def audit_discipline_action(
    *,
    action: str,
    instance: Any,
    description: str,
    actor=None,
    request=None,
    old_values: dict | None = None,
    new_values: dict | None = None,
):
    return log_action(
        request=request,
        actor=actor,
        action=action,
        description=description,
        entity_type=instance._meta.label,
        entity_public_id=getattr(instance, "public_id", ""),
        old_values=old_values,
        new_values=new_values,
    )


__all__ = ["audit_discipline_action"]

