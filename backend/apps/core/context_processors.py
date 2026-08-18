"""Template context processors."""

from django.conf import settings

from apps.core.branding import (
    app_full_name,
    platform_name,
    platform_tagline,
    school_display_name,
    school_display_slogan,
    school_full_name,
)


def school_context(request):
    from apps.core.vite import vite_asset_tags

    school_name = (settings.SCHOOL_NAME or "").strip()
    school_slogan = (settings.SCHOOL_SLOGAN or "").strip()

    return {
        "platform_name": platform_name(),
        "platform_tagline": platform_tagline(),
        "app_full_name": app_full_name(),
        "school_name": school_display_name(),
        "school_slogan": school_display_slogan(),
        "school_full_name": school_full_name(),
        "school_configured": bool(school_name),
        "app_version": settings.APP_VERSION,
        "vite_assets": vite_asset_tags(),
    }


def secretariat_year_context(request):
    """Expose selected academic year to year-scoped modules."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    is_sec = getattr(user, "is_secretaire", lambda: False)()
    is_acc = getattr(user, "is_comptable", lambda: False)()
    is_disc = getattr(user, "has_role", lambda *_: False)("DISCIPLINE")
    is_pref = getattr(user, "is_prefet", lambda: False)()
    if not (is_sec or is_acc or is_disc or is_pref):
        return {}
    from apps.secretariat.services.year_context import year_context_service

    year = year_context_service.get_selected_year(request)
    return {
        "selected_academic_year": year,
        "is_selected_year_closed": bool(year and year.is_closed),
        "secretariat_year_session_key": year_context_service.session_key,
    }
