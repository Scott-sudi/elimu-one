"""BI REST API views — Préfet read-only analytics."""

from __future__ import annotations

from decimal import Decimal

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.api.permissions import IsPrefet
from apps.api.views import envelope
from apps.bi.filters import parse_bi_filters
from apps.bi.services import (
    attendance_analytics_service,
    class_analytics_service,
    comparison_service,
    discipline_analytics_service,
    enrollment_analytics_service,
    financial_analytics_service,
    overview_service,
)
from apps.secretariat.services.year_context import year_context_service


def _serialize(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    return value


def _require_year(request):
    year = year_context_service.get_selected_year(request)
    if year is None:
        return None, envelope(
            success=False,
            message="Aucune année scolaire n'est sélectionnée.",
            errors={"academic_year": "Sélection requise."},
            http_status=400,
        )
    return year, None


class OverviewAPIView(APIView):
    """GET executive overview KPIs for the selected academic year."""

    permission_classes = [IsAuthenticated, IsPrefet]

    def get(self, request):
        year, error = _require_year(request)
        if error:
            return error
        data = overview_service.build_overview(year)
        return envelope(
            message="Vue d'ensemble chargée.",
            data=_serialize(data),
        )


class _DomainAPIView(APIView):
    """Base for domain summary / trends / classes endpoints."""

    permission_classes = [IsAuthenticated, IsPrefet]
    section = "summary"  # summary | trends | classes
    builder = None
    french_domain = "Analyse"

    def get(self, request):
        year, error = _require_year(request)
        if error:
            return error
        filters = parse_bi_filters(request)
        analytics = self.builder(year, filters)
        if self.section == "summary":
            payload = {
                "kpis": analytics["kpis"],
                "filters": analytics.get("filters"),
                "generated_at": analytics.get("generated_at"),
            }
            message = f"{self.french_domain} — synthèse."
        elif self.section == "trends":
            payload = {
                "charts": analytics["charts"],
                "filters": analytics.get("filters"),
                "generated_at": analytics.get("generated_at"),
            }
            message = f"{self.french_domain} — tendances."
        else:
            payload = {
                "tables": analytics.get("tables"),
                "charts": {
                    k: v
                    for k, v in (analytics.get("charts") or {}).items()
                    if "class" in k or k in {"by_class", "occupation", "comparison"}
                },
                "filters": analytics.get("filters"),
                "generated_at": analytics.get("generated_at"),
            }
            message = f"{self.french_domain} — classes."
        return envelope(message=message, data=_serialize(payload))


class EnrollmentSummaryAPIView(_DomainAPIView):
    french_domain = "Effectifs"
    section = "summary"
    builder = staticmethod(enrollment_analytics_service.build_enrollment_analytics)


class EnrollmentTrendsAPIView(_DomainAPIView):
    french_domain = "Effectifs"
    section = "trends"
    builder = staticmethod(enrollment_analytics_service.build_enrollment_analytics)


class EnrollmentClassesAPIView(_DomainAPIView):
    french_domain = "Effectifs"
    section = "classes"
    builder = staticmethod(enrollment_analytics_service.build_enrollment_analytics)


class FinancialSummaryAPIView(_DomainAPIView):
    french_domain = "Finances"
    section = "summary"
    builder = staticmethod(financial_analytics_service.build_financial_analytics)


class FinancialTrendsAPIView(_DomainAPIView):
    french_domain = "Finances"
    section = "trends"
    builder = staticmethod(financial_analytics_service.build_financial_analytics)


class FinancialClassesAPIView(_DomainAPIView):
    french_domain = "Finances"
    section = "classes"
    builder = staticmethod(financial_analytics_service.build_financial_analytics)


class AttendanceSummaryAPIView(_DomainAPIView):
    french_domain = "Assiduité"
    section = "summary"
    builder = staticmethod(attendance_analytics_service.build_attendance_analytics)


class AttendanceTrendsAPIView(_DomainAPIView):
    french_domain = "Assiduité"
    section = "trends"
    builder = staticmethod(attendance_analytics_service.build_attendance_analytics)


class AttendanceClassesAPIView(_DomainAPIView):
    french_domain = "Assiduité"
    section = "classes"
    builder = staticmethod(attendance_analytics_service.build_attendance_analytics)


class DisciplineSummaryAPIView(_DomainAPIView):
    french_domain = "Discipline"
    section = "summary"
    builder = staticmethod(discipline_analytics_service.build_discipline_analytics)


class DisciplineTrendsAPIView(_DomainAPIView):
    french_domain = "Discipline"
    section = "trends"
    builder = staticmethod(discipline_analytics_service.build_discipline_analytics)


class DisciplineClassesAPIView(_DomainAPIView):
    french_domain = "Discipline"
    section = "classes"
    builder = staticmethod(discipline_analytics_service.build_discipline_analytics)


class ClassesSummaryAPIView(_DomainAPIView):
    french_domain = "Classes"
    section = "summary"
    builder = staticmethod(class_analytics_service.build_class_analytics)


class ClassesTrendsAPIView(_DomainAPIView):
    french_domain = "Classes"
    section = "trends"
    builder = staticmethod(class_analytics_service.build_class_analytics)


class ClassesClassesAPIView(_DomainAPIView):
    french_domain = "Classes"
    section = "classes"
    builder = staticmethod(class_analytics_service.build_class_analytics)


class ComparisonsSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPrefet]

    def get(self, request):
        year_ids = request.GET.getlist("year_id") or request.GET.getlist("years")
        parsed = []
        for raw in year_ids:
            try:
                parsed.append(int(raw))
            except (TypeError, ValueError):
                continue
        data = comparison_service.build_year_comparison(year_ids=parsed or None)
        return envelope(
            message="Comparaisons annuelles chargées.",
            data=_serialize(
                {
                    "kpis": data["kpis"],
                    "tables": data["tables"],
                    "generated_at": data["generated_at"],
                }
            ),
        )


class ComparisonsTrendsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPrefet]

    def get(self, request):
        year_ids = request.GET.getlist("year_id") or request.GET.getlist("years")
        parsed = []
        for raw in year_ids:
            try:
                parsed.append(int(raw))
            except (TypeError, ValueError):
                continue
        data = comparison_service.build_year_comparison(year_ids=parsed or None)
        return envelope(
            message="Tendances comparatives chargées.",
            data=_serialize(
                {
                    "charts": data["charts"],
                    "generated_at": data["generated_at"],
                }
            ),
        )
