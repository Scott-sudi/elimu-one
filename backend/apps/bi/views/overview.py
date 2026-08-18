"""BI executive overview page."""

from apps.bi.services import overview_service

from .base import BiPageView


class OverviewView(BiPageView):
    template_name = "bi/overview/index.html"
    page_title = "Vue d'ensemble"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        overview = overview_service.build_overview(year)
        context.update(
            overview=overview,
            kpis=overview["kpis"],
            alerts=overview["alerts"],
            generated_at=overview["generated_at"],
            breadcrumbs=[("Business Intelligence", None)],
        )
        return context
