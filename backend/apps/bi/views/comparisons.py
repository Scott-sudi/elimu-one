"""BI academic-year comparisons page."""

import json

from django.core.serializers.json import DjangoJSONEncoder

from apps.bi.services import comparison_service

from .base import BiPageView


class ComparisonsView(BiPageView):
    template_name = "bi/comparisons/index.html"
    page_title = "Comparaisons"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year_ids = self.request.GET.getlist("year_id") or self.request.GET.getlist("years")
        parsed_ids = []
        for raw in year_ids:
            try:
                parsed_ids.append(int(raw))
            except (TypeError, ValueError):
                continue
        analytics = comparison_service.build_year_comparison(
            year_ids=parsed_ids or None,
        )
        context.update(
            analytics=analytics,
            kpis=analytics["kpis"],
            charts=analytics["charts"],
            tables=analytics["tables"],
            charts_json=json.dumps(analytics["charts"], cls=DjangoJSONEncoder),
            generated_at=analytics["generated_at"],
        )
        return context
