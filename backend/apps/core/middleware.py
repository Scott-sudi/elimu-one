"""Middleware helpers."""

from django.shortcuts import redirect
from django.urls import reverse


class MustChangePasswordMiddleware:
    """Force password change when required."""

    EXEMPT_URL_NAMES = (
        "accounts:login",
        "accounts:logout",
        "accounts:change_password",
        "accounts:profile",
        "setup:setup",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and getattr(user, "must_change_password", False)
            and request.method == "GET"
            and not request.path.startswith("/api/")
            and not request.path.startswith("/setup/")
            and not self._is_exempt_path(request.path)
        ):
            return redirect(f"{reverse('accounts:change_password')}?forced=1")
        return self.get_response(request)

    def _is_exempt_path(self, path: str) -> bool:
        # resolver_match is not available before get_response; compare paths instead.
        for name in self.EXEMPT_URL_NAMES:
            try:
                if path == reverse(name) or path.rstrip("/") == reverse(name).rstrip("/"):
                    return True
            except Exception:
                continue
        return path.startswith("/profil/")
