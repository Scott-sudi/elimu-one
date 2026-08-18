"""URL configuration for Kalunga school project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from apps.core import error_handlers
from apps.core.media_views import cors_media_serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="accounts:login", permanent=False)),
    path("setup/", include(("apps.accounts.urls_setup", "setup"))),
    path("", include(("apps.accounts.urls", "accounts"))),
    path("", include(("apps.dashboard.urls", "dashboard"))),
    path("", include(("apps.audit.urls", "audit"))),
    path("secretariat/", include(("apps.secretariat.urls", "secretariat"))),
    path("comptabilite/", include(("apps.finance.urls", "finance"))),
    path("discipline/", include(("apps.discipline.urls", "discipline"))),
    path("bi/", include(("apps.bi.urls", "bi"))),
    path("api/v1/", include(("apps.api.urls", "api"))),
]

handler400 = error_handlers.handler400
handler403 = error_handlers.handler403
handler404 = error_handlers.handler404
handler500 = error_handlers.handler500

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # o2switch / Passenger : servir /media/ via Django si le symlink Apache
    # n'est pas encore en place (sinon les photos élèves renvoient 404 HTML).
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            cors_media_serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
