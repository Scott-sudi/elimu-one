"""Template context processors."""

from django.conf import settings


def school_context(request):
    from apps.core.vite import vite_asset_tags

    return {
        "school_name": settings.SCHOOL_NAME,
        "school_slogan": settings.SCHOOL_SLOGAN,
        "school_full_name": f"{settings.SCHOOL_NAME} – {settings.SCHOOL_SLOGAN}",
        "app_version": settings.APP_VERSION,
        "vite_assets": vite_asset_tags(),
    }
