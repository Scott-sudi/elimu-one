"""Accountant dashboard."""

from django.urls import reverse
from django.views.generic import TemplateView

from apps.finance.services.dashboard_service import dashboard_stats
from apps.finance.services.fee_service import ensure_default_fee_categories

from .base import FinanceViewMixin


class DashboardView(FinanceViewMixin, TemplateView):
    template_name = "finance/dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ensure_default_fee_categories()
        year = self.require_selected_year()
        context.update(
            stats=dashboard_stats(academic_year=year),
            year_writable=not year.is_closed,
            breadcrumbs=[("Comptabilité", reverse("finance:dashboard"))],
        )
        return context
