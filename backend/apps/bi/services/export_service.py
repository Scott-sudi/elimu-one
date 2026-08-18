"""BI CSV/XLSX export helpers (stubs wired to analytics tables)."""

from __future__ import annotations

import csv
from io import BytesIO
from typing import Any

from django.http import HttpResponse
from openpyxl import Workbook

from apps.bi.filters import BiFilters
from apps.bi.services import (
    attendance_analytics_service,
    class_analytics_service,
    comparison_service,
    discipline_analytics_service,
    enrollment_analytics_service,
    financial_analytics_service,
)
from apps.secretariat.models import AcademicYear

DOMAIN_CHOICES = (
    "enrollments",
    "financial",
    "attendance",
    "discipline",
    "classes",
    "comparisons",
)


def _analytics_payload(
    domain: str,
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> dict[str, Any]:
    if domain == "enrollments":
        return enrollment_analytics_service.build_enrollment_analytics(
            academic_year, filters
        )
    if domain == "financial":
        return financial_analytics_service.build_financial_analytics(
            academic_year, filters
        )
    if domain == "attendance":
        return attendance_analytics_service.build_attendance_analytics(
            academic_year, filters
        )
    if domain == "discipline":
        return discipline_analytics_service.build_discipline_analytics(
            academic_year, filters
        )
    if domain == "classes":
        return class_analytics_service.build_class_analytics(academic_year, filters)
    if domain == "comparisons":
        return comparison_service.build_year_comparison()
    raise ValueError(f"Domaine d'export inconnu : {domain}")


def _flatten_rows(domain: str, payload: dict[str, Any]) -> tuple[list[str], list[list[Any]]]:
    tables = payload.get("tables") or {}
    if domain == "enrollments":
        rows = tables.get("occupation") or []
        headers = [
            "Classe",
            "Niveau",
            "Capacité",
            "Effectif",
            "Places restantes",
            "Taux occupation",
            "Statut",
        ]
        data = [
            [
                r.get("name"),
                r.get("level"),
                r.get("capacity"),
                r.get("effectif"),
                r.get("places_restantes"),
                r.get("taux_occupation"),
                r.get("statut"),
            ]
            for r in rows
        ]
        return headers, data
    if domain == "financial":
        rows = tables.get("by_class") or []
        headers = [
            "Classe",
            "Attendu",
            "Encaissé",
            "Solde",
            "Taux recouvrement",
            "Nb paiements",
        ]
        data = [
            [
                r.get("name"),
                r.get("montant_attendu"),
                r.get("montant_encaisse"),
                r.get("solde"),
                r.get("taux_recouvrement"),
                r.get("nb_paiements"),
            ]
            for r in rows
        ]
        return headers, data
    if domain == "attendance":
        rows = tables.get("by_class") or []
        headers = ["Classe", "Total", "Présents+", "Retards", "Absences", "Taux présence"]
        data = [
            [
                r.get("name"),
                r.get("total"),
                r.get("present_like"),
                r.get("late"),
                r.get("absent"),
                r.get("taux_presence"),
            ]
            for r in rows
        ]
        return headers, data
    if domain == "discipline":
        rows = tables.get("by_class") or []
        headers = ["Classe", "Incidents", "Ouverts"]
        data = [
            [r.get("school_class__name"), r.get("total"), r.get("ouverts")]
            for r in rows
        ]
        return headers, data
    if domain == "classes":
        rows = tables.get("classes") or []
        headers = [
            "Classe",
            "Niveau",
            "Effectif",
            "Capacité",
            "Occupation %",
            "Statut",
            "Recouvrement %",
            "Présence %",
            "Incidents ouverts",
        ]
        data = [
            [
                r.get("name"),
                r.get("level"),
                r.get("effectif"),
                r.get("capacity"),
                r.get("taux_occupation"),
                r.get("statut"),
                r.get("taux_recouvrement"),
                r.get("taux_presence"),
                r.get("incidents_ouverts"),
            ]
            for r in rows
        ]
        return headers, data
    rows = tables.get("years") or []
    headers = [
        "Année",
        "Effectif",
        "Classes",
        "Occupation %",
        "Attendu",
        "Encaissé",
        "Recouvrement %",
        "Présence %",
        "Incidents ouverts",
    ]
    data = [
        [
            r.get("label"),
            r.get("effectif_total"),
            r.get("classes_actives"),
            r.get("occupation_moyenne"),
            r.get("montant_attendu"),
            r.get("montant_encaisse"),
            r.get("taux_recouvrement"),
            r.get("taux_presence"),
            r.get("incidents_ouverts"),
        ]
        for r in rows
    ]
    return headers, data


def available_exports() -> list[dict[str, str]]:
    return [
        {"domain": "enrollments", "label": "Effectifs par classe", "formats": "csv,xlsx"},
        {"domain": "financial", "label": "Finances par classe", "formats": "csv,xlsx"},
        {"domain": "attendance", "label": "Assiduité par classe", "formats": "csv,xlsx"},
        {"domain": "discipline", "label": "Discipline par classe", "formats": "csv,xlsx"},
        {"domain": "classes", "label": "Synthèse des classes", "formats": "csv,xlsx"},
        {"domain": "comparisons", "label": "Comparaisons annuelles", "formats": "csv,xlsx"},
    ]


def build_export_response(
    *,
    domain: str,
    academic_year: AcademicYear,
    file_format: str = "csv",
    filters: BiFilters | None = None,
) -> HttpResponse:
    """Return an HttpResponse with CSV or XLSX content (secretariat export pattern)."""
    domain = (domain or "").lower()
    if domain not in DOMAIN_CHOICES:
        domain = "enrollments"
    file_format = (file_format or "csv").lower()
    if file_format not in {"csv", "xlsx"}:
        file_format = "csv"

    payload = _analytics_payload(domain, academic_year, filters)
    headers, rows = _flatten_rows(domain, payload)
    filename = f"bi_{domain}.{file_format}"

    if file_format == "xlsx":
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Export BI"
        sheet.append(headers)
        for row in rows:
            sheet.append([_cell(v) for v in row])
        output = BytesIO()
        workbook.save(output)
        response = HttpResponse(
            output.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
    else:
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([_cell(v) for v in row])

    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    return value


def report_preview(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> dict[str, Any]:
    """Lightweight payload for the reports page."""
    from apps.bi.services import overview_service

    overview = overview_service.build_overview(academic_year)
    return {
        "kpis": overview["kpis"],
        "exports": available_exports(),
        "charts": {
            "preview": {
                "labels": ["Effectif", "Classes", "Incidents ouverts", "Retards"],
                "series": [
                    {
                        "name": "Indicateurs",
                        "data": [
                            overview["kpis"]["effectif_total"],
                            overview["kpis"]["classes_actives"],
                            overview["kpis"]["incidents_ouverts"],
                            overview["kpis"]["retards"],
                        ],
                    }
                ],
            },
            "exports": {
                "labels": [e["label"] for e in available_exports()],
                "series": [
                    {
                        "name": "Disponibles",
                        "data": [1 for _ in available_exports()],
                    }
                ],
            },
        },
        "tables": {
            "exports": available_exports(),
        },
        "filters": (filters or BiFilters()).as_dict(),
        "generated_at": timezone_now_safe(overview),
    }


def timezone_now_safe(overview: dict[str, Any]):
    return overview.get("generated_at")
