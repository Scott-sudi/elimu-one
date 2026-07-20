"""Middleware helpers."""

from django.shortcuts import redirect
from django.urls import reverse


class MustChangePasswordMiddleware:
    """Force password change when required."""

    EXEMPT_NAMES = {
        "accounts:login",
        "accounts:logout",
        "accounts:change_password",
        "accounts:profile",
        "setup:setup",
        "setup:status",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and getattr(user, "must_change_password", False)
            and request.method == "GET"
        ):
            try:
                match = request.resolver_match
                name = f"{match.namespace}:{match.url_name}" if match and match.namespace else (match.url_name if match else "")
            except Exception:
                name = ""
            if name not in self.EXEMPT_NAMES and not request.path.startswith("/api/"):
                return redirect(reverse("accounts:change_password") + "?forced=1")
        return self.get_response(request)
