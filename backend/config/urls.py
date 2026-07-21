"""URL configuration for Kalunga school project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from apps.core import error_handlers

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="accounts:login", permanent=False)),
    path("setup/", include(("apps.accounts.urls_setup", "setup"))),
    path("", include(("apps.accounts.urls", "accounts"))),
    path("", include(("apps.dashboard.urls", "dashboard"))),
    path("", include(("apps.audit.urls", "audit"))),
    path("secretariat/", include(("apps.secretariat.urls", "secretariat"))),
    path("api/v1/", include(("apps.api.urls", "api"))),
]

handler400 = error_handlers.handler400
handler403 = error_handlers.handler403
handler404 = error_handlers.handler404
handler500 = error_handlers.handler500

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
