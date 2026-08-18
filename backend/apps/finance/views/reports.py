"""Finance reports and CSV / XLSX / PDF exports."""

from __future__ import annotations

import csv
from datetime import datetime
from io import BytesIO

from django.http import HttpResponse
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from apps.finance.models import Payment
from apps.finance.services.situation_service import arrears_queryset

from .base import FinanceViewMixin


PAYMENT_HEADERS = [
    "Reçu",
    "Date",
    "Matricule",
    "Élève",
    "Classe",
    "Montant",
    "Devise",
    "Mode",
    "Référence",
]

ARREARS_HEADERS = [
    "Matricule",
    "Élève",
    "Classe",
    "Frais",
    "Code",
    "Dû",
    "Payé",
    "Solde",
    "Devise",
    "Statut",
]


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d")


def _payment_queryset(year, date_from: str, date_to: str):
    qs = (
        Payment.objects.filter(
            academic_year=year,
            status=Payment.Status.VALID,
        )
        .select_related("student", "enrollment__school_class")
        .order_by("payment_date", "receipt_number")
    )
    if date_from:
        qs = qs.filter(payment_date__gte=date_from)
    if date_to:
        qs = qs.filter(payment_date__lte=date_to)
    return qs


def _payment_rows(qs):
    for payment in qs:
        student = payment.student
        yield [
            payment.receipt_number,
            payment.payment_date.strftime("%d/%m/%Y"),
            student.matricule,
            f"{student.nom} {student.postnom} {student.prenom}".strip(),
            payment.enrollment.school_class.name,
            str(payment.amount_total),
            payment.currency,
            payment.get_payment_method_display(),
            payment.transaction_reference,
        ]


def _arrears_rows(qs):
    for obligation in qs:
        student = obligation.student
        yield [
            student.matricule,
            f"{student.nom} {student.postnom} {student.prenom}".strip(),
            obligation.enrollment.school_class.name,
            obligation.fee.label,
            obligation.fee.code,
            str(obligation.amount_due),
            str(obligation.amount_paid),
            str(obligation.amount_remaining),
            obligation.fee.currency,
            obligation.get_status_display(),
        ]


def _csv_response(filename: str, headers: list[str], rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(headers)
    writer.writerows(rows)
    return response


def _xlsx_response(filename: str, headers: list[str], rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Export"
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    response = HttpResponse(
        output.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _pdf_table_response(filename: str, title: str, headers: list[str], rows):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 20 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(15 * mm, y, title)
    y -= 10 * mm
    pdf.setFont("Helvetica", 8)
    header_line = " | ".join(headers[:6])
    pdf.drawString(15 * mm, y, header_line[:110])
    y -= 6 * mm
    for row in rows:
        if y < 20 * mm:
            pdf.showPage()
            y = height - 20 * mm
            pdf.setFont("Helvetica", 8)
        line = " | ".join(str(cell) for cell in row[:6])
        pdf.drawString(15 * mm, y, line[:110])
        y -= 5 * mm
    pdf.save()
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


class ReportsIndexView(FinanceViewMixin, TemplateView):
    template_name = "finance/reports/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            ("Comptabilité", reverse("finance:dashboard")),
            ("Rapports", None),
        ]
        return context


class PaymentsPeriodExportView(FinanceViewMixin, View):
    """Export valid payments for a date range (csv / xlsx / pdf)."""

    def get(self, request):
        year = self.require_selected_year()
        date_from = request.GET.get("date_from", "").strip()
        date_to = request.GET.get("date_to", "").strip()
        path = request.path.lower()
        if path.endswith(".xlsx"):
            fmt = "xlsx"
        elif path.endswith(".pdf"):
            fmt = "pdf"
        else:
            fmt = (request.GET.get("format") or "csv").strip().lower()
        if fmt not in {"csv", "xlsx", "pdf"}:
            fmt = "csv"

        qs = _payment_queryset(year, date_from, date_to)
        rows = list(_payment_rows(qs))
        stamp = _stamp()
        base = f"paiements_{year.label}_{stamp}"

        if fmt == "xlsx":
            return _xlsx_response(f"{base}.xlsx", PAYMENT_HEADERS, rows)
        if fmt == "pdf":
            return _pdf_table_response(
                f"{base}.pdf",
                f"Paiements — {year.label}",
                PAYMENT_HEADERS,
                rows,
            )
        return _csv_response(f"{base}.csv", PAYMENT_HEADERS, rows)


class ArrearsExportView(FinanceViewMixin, View):
    """Export current arrears for the selected year (csv / xlsx / pdf)."""

    def get(self, request):
        year = self.require_selected_year()
        fmt = (request.GET.get("format") or "csv").strip().lower()
        if fmt not in {"csv", "xlsx", "pdf"}:
            fmt = "csv"

        qs = arrears_queryset(academic_year=year).select_related(
            "student",
            "enrollment__school_class",
            "fee",
        )
        rows = list(_arrears_rows(qs))
        stamp = _stamp()
        base = f"impayes_{year.label}_{stamp}"

        if fmt == "xlsx":
            return _xlsx_response(f"{base}.xlsx", ARREARS_HEADERS, rows)
        if fmt == "pdf":
            return _pdf_table_response(
                f"{base}.pdf",
                f"Impayés — {year.label}",
                ARREARS_HEADERS,
                rows,
            )
        return _csv_response(f"{base}.csv", ARREARS_HEADERS, rows)
