"""Secretary dashboard."""

from django.urls import reverse
from django.views.generic import TemplateView

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.models import Enrollment
from apps.secretariat.services.dashboard_service import get_dashboard_stats


class DashboardView(SecretaryRequiredMixin, TemplateView):
    template_name = "secretariat/dashboard/index.html"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["secretariat/dashboard/_stats.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = get_dashboard_stats()
        context.update(
            stats=stats,
            recent_enrollments=Enrollment.objects.select_related(
                "student", "school_class", "academic_year"
            )[:8],
            breadcrumbs=[("Secrétariat", reverse("secretariat:dashboard"))],
        )
        return context
