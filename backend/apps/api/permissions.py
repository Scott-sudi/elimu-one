"""API permission classes."""

from rest_framework.permissions import BasePermission

from apps.accounts.models import Role


class HasRole(BasePermission):
    message = "Vous ne disposez pas de cette autorisation."
    allowed_roles: tuple[str, ...] = ()

    def has_permission(self, request, view):
        user = request.user
        if not (
            user
            and user.is_authenticated
            and user.is_active
            and not getattr(user, "is_archived", False)
        ):
            return False
        roles = getattr(view, "allowed_roles", None) or self.allowed_roles
        if not roles:
            return True
        return any(hasattr(user, "has_role") and user.has_role(code) for code in roles)


class IsAdministrator(HasRole):
    allowed_roles = (Role.CODE_ADMINISTRATEUR,)


class IsSecretary(HasRole):
    allowed_roles = (Role.CODE_SECRETAIRE,)
