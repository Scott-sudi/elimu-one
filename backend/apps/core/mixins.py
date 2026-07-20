"""Common mixins for views."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class AdministratorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict access to authenticated administrators."""

    def test_func(self):
        user = self.request.user
        return (
            user.is_authenticated
            and user.is_active
            and not user.is_archived
            and user.is_administrateur()
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Vous ne disposez pas de cette autorisation.")
        return super().handle_no_permission()


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
