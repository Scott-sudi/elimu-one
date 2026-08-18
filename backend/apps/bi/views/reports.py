"""BI reports / exports page."""

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponseBadRequest
from django.views import View

from apps.bi.filters import parse_bi_filters
from apps.bi.services import export_service
from apps.core.mixins import PrefetRequiredMixin

from .base import BiAcademicYearRequiredMixin, BiPageView


class ReportsView(BiPageView):
    template_name = "bi/reports/index.html"
    page_title = "Rapports"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        filters = parse_bi_filters(self.request)
        analytics = export_service.report_preview(year, filters)
        context.update(
            analytics=analytics,
            kpis=analytics["kpis"],
            charts=analytics["charts"],
            tables=analytics["tables"],
            exports=analytics["exports"],
            charts_json=json.dumps(analytics["charts"], cls=DjangoJSONEncoder),
            filters=filters,
            generated_at=analytics["generated_at"],
        )
        return context


class BiExportDownloadView(PrefetRequiredMixin, BiAcademicYearRequiredMixin, View):
    """CSV/XLSX download endpoint for BI domain tables."""

    def get(self, request, domain, file_format="csv"):
        year = self.require_selected_year()
        filters = parse_bi_filters(request)
        try:
            return export_service.build_export_response(
                domain=domain,
                academic_year=year,
                file_format=file_format,
                filters=filters,
            )
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))
