"""Receipt views."""

from io import BytesIO

from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import DetailView

from apps.finance.models import Payment
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.receipt_service import build_receipt_pdf

from .base import FinanceListView, FinanceViewMixin


class ReceiptListView(FinanceListView):
    """List of issued receipts (valid payments) with consult / download actions."""

    template_name = "finance/receipts/list.html"
    partial_template_name = "finance/receipts/_table.html"
    context_object_name = "receipts"
    page_title = "Reçus"

    def get_queryset(self):
        year = self.require_selected_year()
        qs = (
            Payment.objects.filter(
                academic_year=year,
                status=Payment.Status.VALID,
            )
            .select_related(
                "student",
                "enrollment",
                "enrollment__school_class",
                "recorded_by",
            )
            .order_by("-payment_date", "-created_at")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(receipt_number__icontains=q)
                | Q(student__matricule__icontains=q)
                | Q(student__nom__icontains=q)
                | Q(student__prenom__icontains=q)
                | Q(student__postnom__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_filters"] = {"q": self.request.GET.get("q", "")}
        return context


class ReceiptDetailView(FinanceViewMixin, DetailView):
    model = Payment
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "payment"
    template_name = "finance/receipts/detail.html"

    def get_queryset(self):
        year = self.require_selected_year()
        return (
            Payment.objects.filter(academic_year=year)
            .select_related(
                "student",
                "enrollment",
                "enrollment__school_class",
                "academic_year",
                "recorded_by",
            )
            .prefetch_related("allocations__obligation__fee")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment = self.object
        context["breadcrumbs"] = [
            ("Comptabilité", reverse("finance:dashboard")),
            ("Reçus", reverse("finance:receipts")),
            (payment.receipt_number, None),
        ]
        return context


@method_decorator(xframe_options_sameorigin, name="dispatch")
class ReceiptPDFView(FinanceViewMixin, View):
    def get(self, request, public_id):
        payment = get_object_or_404(
            Payment,
            public_id=public_id,
            academic_year=self.require_selected_year(),
        )
        inline = request.GET.get("inline") == "1"
        try:
            content = build_receipt_pdf(
                payment=payment,
                actor=request.user,
                request=request,
                audit=not inline,
            )
        except FinanceError as exc:
            messages.error(request, str(exc))
            return redirect("finance:receipts")
        return FileResponse(
            BytesIO(content),
            content_type="application/pdf",
            as_attachment=not inline,
            filename=f"{payment.receipt_number}.pdf",
        )
