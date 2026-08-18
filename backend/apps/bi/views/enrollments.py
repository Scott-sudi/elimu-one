"""BI enrollments analytics page."""

import json

from django.core.serializers.json import DjangoJSONEncoder

from apps.bi.filters import parse_bi_filters
from apps.bi.services import enrollment_analytics_service

from .base import BiPageView


class EnrollmentsView(BiPageView):
    template_name = "bi/enrollments/index.html"
    page_title = "Effectifs"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        filters = parse_bi_filters(self.request)
        analytics = enrollment_analytics_service.build_enrollment_analytics(year, filters)
        context.update(
            analytics=analytics,
            kpis=analytics["kpis"],
            charts=analytics["charts"],
            tables=analytics["tables"],
            charts_json=json.dumps(analytics["charts"], cls=DjangoJSONEncoder),
            filters=filters,
            generated_at=analytics["generated_at"],
        )
        return context
