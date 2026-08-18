"""Secretary dashboard."""

from django.urls import reverse
from django.views.generic import TemplateView

from apps.secretariat.services.dashboard_service import get_dashboard_stats
from apps.secretariat.services.year_context import year_context_service

from .base import SecretariatViewMixin


class DashboardView(SecretariatViewMixin, TemplateView):
    template_name = "secretariat/dashboard/index.html"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["secretariat/dashboard/_stats.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = year_context_service.get_selected_year(self.request)
        context.update(
            stats=get_dashboard_stats(academic_year=year),
            breadcrumbs=[("Secrétariat", reverse("secretariat:dashboard"))],
        )
        return context
