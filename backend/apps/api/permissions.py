"""API permission classes."""

from rest_framework.permissions import BasePermission


class IsAdministrator(BasePermission):
    message = "Vous ne disposez pas de cette autorisation."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and not getattr(user, "is_archived", False)
            and hasattr(user, "is_administrateur")
            and user.is_administrateur()
        )
