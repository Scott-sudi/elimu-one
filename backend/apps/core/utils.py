"""Shared utilities, mixins, and responses."""

from __future__ import annotations

from typing import Any

from django.http import JsonResponse


def api_response(
    *,
    success: bool = True,
    message: str = "",
    data: Any = None,
    errors: Any = None,
    status: int = 200,
) -> JsonResponse:
    return JsonResponse(
        {
            "success": success,
            "message": message,
            "data": data if data is not None else {},
            "errors": errors if errors is not None else {},
        },
        status=status,
    )


def get_client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def parse_user_agent(user_agent: str) -> dict[str, str]:
    """Lightweight user-agent parsing without external dependency."""
    ua = user_agent or ""
    browser = "Inconnu"
    os_name = "Inconnu"
    device = "Ordinateur"

    ua_lower = ua.lower()
    if "edg/" in ua_lower:
        browser = "Microsoft Edge"
    elif "chrome/" in ua_lower and "chromium" not in ua_lower:
        browser = "Chrome"
    elif "firefox/" in ua_lower:
        browser = "Firefox"
    elif "safari/" in ua_lower and "chrome" not in ua_lower:
        browser = "Safari"
    elif "opera" in ua_lower or "opr/" in ua_lower:
        browser = "Opera"

    if "windows" in ua_lower:
        os_name = "Windows"
    elif "mac os" in ua_lower or "macintosh" in ua_lower:
        os_name = "macOS"
    elif "android" in ua_lower:
        os_name = "Android"
        device = "Mobile"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
        device = "Mobile" if "iphone" in ua_lower else "Tablette"
    elif "linux" in ua_lower:
        os_name = "Linux"

    if "mobile" in ua_lower and device == "Ordinateur":
        device = "Mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device = "Tablette"

    return {"browser": browser, "operating_system": os_name, "device": device}
