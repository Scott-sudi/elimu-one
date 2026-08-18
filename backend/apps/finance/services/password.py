"""Password confirmation helpers for sensitive finance actions."""

from __future__ import annotations

from apps.finance.services.exceptions import FinanceError


def require_password(request, *, field_name: str = "password") -> None:
    """Validate the current user's password from the request body.

    Raises FinanceError when the password is missing or incorrect.
    """
    password = ""
    if hasattr(request, "POST"):
        password = (request.POST.get(field_name) or "").strip()
    if not password and hasattr(request, "data"):
        raw = request.data.get(field_name, "")
        password = str(raw).strip() if raw is not None else ""
    if not password:
        raise FinanceError("Saisissez votre mot de passe pour confirmer cette action.")
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        raise FinanceError("Authentification requise.")
    if not user.check_password(password):
        raise FinanceError("Mot de passe incorrect.")
