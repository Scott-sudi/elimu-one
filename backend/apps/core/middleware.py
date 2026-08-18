"""Middleware helpers."""

from urllib.parse import urlparse

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class SameOriginCsrfBypassMiddleware:
    """Accept POST when Origin/Referer is this site.

    Some browsers (HTTP, self-signed HTTPS, privacy extensions) drop the
    csrftoken cookie even though Django sends Set-Cookie. Modern browsers
    still send Origin on POST; matching it to ALLOWED_HOSTS is sufficient
    CSRF protection. Must run *before* CsrfViewMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            if self._is_same_origin(request):
                request.csrf_processing_done = True
        return self.get_response(request)

    def _is_same_origin(self, request) -> bool:
        allowed = {h.lower() for h in settings.ALLOWED_HOSTS if h and h != "*"}
        raw = (request.META.get("HTTP_ORIGIN") or request.META.get("HTTP_REFERER") or "").strip()
        if not raw or raw.lower() == "null":
            return False
        hostname = (urlparse(raw).hostname or "").lower()
        if not hostname:
            return False
        return hostname in allowed


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
