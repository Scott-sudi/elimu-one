"""School fee views (accountant)."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView, TemplateView

from apps.finance.forms import SchoolFeeForm
from apps.finance.models import FeeAmountChangeRequest, SchoolFee
from apps.finance.services import fee_service
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.fee_service import (
    archive_fee,
    create_draft_fee,
    ensure_default_fee_categories,
    submit_fee,
    withdraw_fee,
)
from apps.finance.services.password import require_password
from apps.finance.services.payment_sequence_service import fee_period_short_label

from .base import FinanceListView, FinanceViewMixin, ServiceFormMixin


class FeeListView(FinanceListView):
    template_name = "finance/fees/list.html"
    partial_template_name = "finance/fees/_table.html"
    context_object_name = "fees"
    page_title = "Frais scolaires"

    def get_queryset(self):
        year = self.require_selected_year()
        qs = (
            SchoolFee.objects.filter(academic_year=year, is_archived=False)
            .select_related("category", "created_by", "reviewed_by")
            .order_by("-created_at")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(code__icontains=q)
                | Q(label__icontains=q)
                | Q(category__name__icontains=q)
            )
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            status_choices=SchoolFee.Status.choices,
            current_filters={
                "q": self.request.GET.get("q", ""),
                "status": self.request.GET.get("status", ""),
            },
        )
        return context


class FeeRequestsListView(FinanceViewMixin, TemplateView):
    """Accountant view of pending fee creations and amount-change requests."""

    template_name = "finance/fees/requests.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        q = self.request.GET.get("q", "").strip()

        pending_fees = (
            SchoolFee.objects.filter(
                academic_year=year,
                status=SchoolFee.Status.PENDING,
            )
            .select_related("category", "created_by")
            .order_by("-submitted_at", "-created_at")
        )
        amount_changes = (
            FeeAmountChangeRequest.objects.filter(
                fee__academic_year=year,
                status=FeeAmountChangeRequest.Status.PENDING,
            )
            .select_related(
                "fee",
                "fee__category",
                "origin_class",
                "requested_by",
            )
            .prefetch_related("target_classes")
            .order_by("-submitted_at", "-created_at")
        )
        if q:
            pending_fees = pending_fees.filter(
                Q(code__icontains=q)
                | Q(label__icontains=q)
                | Q(category__name__icontains=q)
            )
            amount_changes = amount_changes.filter(
                Q(fee__code__icontains=q)
                | Q(fee__label__icontains=q)
                | Q(origin_class__name__icontains=q)
            )

        amount_rows = [
            {
                "change": change,
                "period_label": fee_period_short_label(change.fee),
            }
            for change in amount_changes
        ]

        context.update(
            pending_fees=list(pending_fees),
            amount_changes=amount_rows,
            current_filters={"q": q},
            year_writable=bool(year and not year.is_closed),
            breadcrumbs=[
                ("Comptabilité", reverse("finance:dashboard")),
                ("Demandes", None),
            ],
        )
        return context


# Backward-compatible name used by urls / exports
FeeRequestsRedirectView = FeeRequestsListView


class FeeCreateView(FinanceViewMixin, ServiceFormMixin, FormView):
    form_class = SchoolFeeForm
    template_name = "finance/fees/create.html"
    success_message = "Frais créé en brouillon."

    def dispatch(self, request, *args, **kwargs):
        try:
            self.require_writable_academic_year()
        except FinanceError as exc:
            messages.error(request, str(exc))
            return redirect("finance:fees")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        from apps.finance.models import FeeCategory

        kwargs = super().get_form_kwargs()
        ensure_default_fee_categories()
        kwargs["academic_year"] = self.require_selected_year()
        kwargs["categories"] = FeeCategory.objects.filter(is_active=True).order_by(
            "order", "name"
        )
        return kwargs

    def execute_service(self, form):
        year = self.require_writable_academic_year()
        return create_draft_fee(
            academic_year=year,
            actor=self.request.user,
            request=self.request,
            **form.service_kwargs(),
        )

    def get_success_url(self):
        return reverse("finance:fee-detail", args=[self.object.public_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            ("Comptabilité", reverse("finance:dashboard")),
            ("Frais", reverse("finance:fees")),
            ("Nouveau", None),
        ]
        return context


class FeeDetailView(FinanceViewMixin, DetailView):
    model = SchoolFee
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "fee"
    template_name = "finance/fees/detail.html"

    def get_queryset(self):
        year = self.require_selected_year()
        return (
            SchoolFee.objects.filter(academic_year=year)
            .select_related("category", "academic_year", "created_by", "reviewed_by")
            .prefetch_related(
                "targets__school_class",
                "targets__level",
                "targets__section",
                "targets__option",
                "approval_history__actor",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_academic_year()
        fee = self.object
        context.update(
            year_writable=bool(year and not year.is_closed),
            can_submit=fee.status in {
                SchoolFee.Status.DRAFT,
                SchoolFee.Status.REJECTED,
            }
            and not fee.is_archived
            and year
            and not year.is_closed,
            can_withdraw=fee.status == SchoolFee.Status.PENDING
            and year
            and not year.is_closed,
            can_archive=not fee.is_archived
            and fee.status != SchoolFee.Status.PENDING
            and year
            and not year.is_closed,
            target_classes=fee_service.resolve_target_classes(fee),
            breadcrumbs=[
                ("Comptabilité", reverse("finance:dashboard")),
                ("Frais", reverse("finance:fees")),
                (fee.label, None),
            ],
        )
        return context


class FeePasswordActionView(FinanceViewMixin, View):
    """POST actions that require password confirmation."""

    action = ""

    def post(self, request, public_id):
        fee = get_object_or_404(
            SchoolFee,
            public_id=public_id,
            academic_year=self.require_selected_year(),
        )
        try:
            self.require_writable_academic_year()
            require_password(request)
            if self.action == "submit":
                submit_fee(fee=fee, actor=request.user, request=request)
                messages.success(request, "Frais soumis pour validation.")
            elif self.action == "withdraw":
                withdraw_fee(fee=fee, actor=request.user, request=request)
                messages.success(request, "Demande retirée.")
            elif self.action == "archive":
                archive_fee(fee=fee, actor=request.user, request=request)
                messages.success(request, "Frais archivé.")
            else:
                messages.error(request, "Action invalide.")
        except FinanceError as exc:
            messages.error(request, str(exc))
        return redirect("finance:fee-detail", public_id=public_id)


class FeeSubmitView(FeePasswordActionView):
    action = "submit"


class FeeWithdrawView(FeePasswordActionView):
    action = "withdraw"


class FeeArchiveView(FeePasswordActionView):
    action = "archive"
