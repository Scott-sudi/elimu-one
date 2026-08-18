"""Platform vs. tenant school display helpers."""

from django.conf import settings


def platform_name() -> str:
    return getattr(settings, "PLATFORM_NAME", "ELIMU One")


def platform_tagline() -> str:
    return getattr(settings, "PLATFORM_TAGLINE", "Système de gestion scolaire")


def school_display_name() -> str:
    """Name printed on cards, receipts, PDFs (tenant school)."""
    value = (getattr(settings, "SCHOOL_NAME", None) or "").strip()
    return value or "Établissement scolaire"


def school_display_slogan() -> str:
    value = (getattr(settings, "SCHOOL_SLOGAN", None) or "").strip()
    return value


def school_full_name() -> str:
    name = school_display_name()
    slogan = school_display_slogan()
    if slogan:
        return f"{name} – {slogan}"
    return name


def app_full_name() -> str:
    """Web shell title / login — product identity."""
    return f"{platform_name()} – {platform_tagline()}"
