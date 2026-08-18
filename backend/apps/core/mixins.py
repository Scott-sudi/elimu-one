"""Common mixins for views."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

from apps.accounts.models import Role


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict access to users with one of the allowed role codes."""

    allowed_roles: tuple[str, ...] = ()

    def test_func(self):
        user = self.request.user
        if not (
            user.is_authenticated
            and user.is_active
            and not user.is_archived
            and not user.is_locked()
        ):
            return False
        if not self.allowed_roles:
            return True
        return any(user.has_role(code) for code in self.allowed_roles)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Vous ne disposez pas de cette autorisation.")
        return super().handle_no_permission()


class AdministratorRequiredMixin(RoleRequiredMixin):
    """Restrict access to authenticated administrators."""

    allowed_roles = (Role.CODE_ADMINISTRATEUR,)


class SecretaryRequiredMixin(RoleRequiredMixin):
    """Restrict access to authenticated secretaries."""

    allowed_roles = (Role.CODE_SECRETAIRE,)


class AccountantRequiredMixin(RoleRequiredMixin):
    """Restrict access to authenticated accountants."""

    allowed_roles = (Role.CODE_COMPTABLE,)


class DisciplineRequiredMixin(RoleRequiredMixin):
    """Restrict access to authenticated discipline staff."""

    allowed_roles = (Role.CODE_DISCIPLINE,)


class PrefetRequiredMixin(RoleRequiredMixin):
    """Restrict access to authenticated prefets (BI read-only)."""

    allowed_roles = (Role.CODE_PREFET,)


class YearOperatorRequiredMixin(RoleRequiredMixin):
    """Secrétaire, Comptable, Discipline ou Préfet — sélection d'année partagée."""

    allowed_roles = (
        Role.CODE_SECRETAIRE,
        Role.CODE_COMPTABLE,
        Role.CODE_DISCIPLINE,
        Role.CODE_PREFET,
    )


class StaffActiveRequiredMixin(LoginRequiredMixin):
    """Ensure the account can use the application."""

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and (not user.is_active or user.is_archived or user.is_locked()):
            from django.contrib.auth import logout

            logout(request)
            from django.shortcuts import redirect

            return redirect("accounts:login")
        return super().dispatch(request, *args, **kwargs)
