"""Secretary fee approval views (fees + amount change requests)."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView

from apps.finance.models import FeeAmountChangeRequest, SchoolFee
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.fee_amount_change_service import (
    approve_amount_change,
    reject_amount_change,
    resolve_change_target_classes,
)
from apps.finance.services.fee_approval_service import approve_fee, reject_fee
from apps.finance.services.fee_service import resolve_target_classes
from apps.finance.services.password import require_password
from apps.finance.services.payment_sequence_service import fee_period_short_label
from apps.secretariat.services.exceptions import SecretariatError
from apps.secretariat.views.base import SecretariatListView, SecretariatViewMixin


def _action_error_message(exc: Exception) -> str:
    return str(exc)


class FeeApprovalListView(SecretariatListView):
    template_name = "secretariat/fee_approvals/list.html"
    partial_template_name = "secretariat/fee_approvals/_table.html"
    context_object_name = "fees"
    page_title = "Validation des frais"

    def get_queryset(self):
        year = self.require_selected_year()
        qs = (
            SchoolFee.objects.filter(
                academic_year=year,
                status=SchoolFee.Status.PENDING,
            )
            .select_related("category", "created_by")
            .order_by("-submitted_at", "-created_at")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(code__icontains=q)
                | Q(label__icontains=q)
                | Q(category__name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_academic_year()
        q = self.request.GET.get("q", "").strip()
        amount_qs = (
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
            amount_qs = amount_qs.filter(
                Q(fee__code__icontains=q)
                | Q(fee__label__icontains=q)
                | Q(origin_class__name__icontains=q)
            )
        context["current_filters"] = {"q": q}
        context["year_writable"] = bool(year and not year.is_closed)
        context["amount_changes"] = list(amount_qs)
        return context


class FeeApprovalDetailView(SecretariatViewMixin, DetailView):
    model = SchoolFee
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "fee"
    template_name = "secretariat/fee_approvals/detail.html"

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
            can_decide=fee.status == SchoolFee.Status.PENDING
            and year
            and not year.is_closed,
            target_classes=resolve_target_classes(fee),
            breadcrumbs=[
                ("Secrétariat", reverse("secretariat:dashboard")),
                ("Validation des frais", reverse("secretariat:fee-approvals")),
                (fee.label, None),
            ],
        )
        return context


class FeeApproveView(SecretariatViewMixin, View):
    def post(self, request, public_id):
        fee = get_object_or_404(
            SchoolFee,
            public_id=public_id,
            academic_year=self.require_selected_year(),
        )
        try:
            self.require_writable_academic_year()
            require_password(request)
            approve_fee(
                fee=fee,
                actor=request.user,
                request=request,
                comment=request.POST.get("comment", ""),
            )
            messages.success(request, "Frais approuvé.")
        except (FinanceError, SecretariatError) as exc:
            messages.error(request, _action_error_message(exc))
        next_url = request.POST.get("next") or ""
        if next_url.startswith("/"):
            return redirect(next_url)
        return redirect("secretariat:fee-approvals")


class FeeRejectView(SecretariatViewMixin, View):
    def post(self, request, public_id):
        fee = get_object_or_404(
            SchoolFee,
            public_id=public_id,
            academic_year=self.require_selected_year(),
        )
        try:
            self.require_writable_academic_year()
            require_password(request)
            reject_fee(
                fee=fee,
                reason=request.POST.get("rejection_reason", ""),
                actor=request.user,
                request=request,
            )
            messages.success(request, "Frais rejeté.")
        except (FinanceError, SecretariatError) as exc:
            messages.error(request, _action_error_message(exc))
        next_url = request.POST.get("next") or ""
        if next_url.startswith("/"):
            return redirect(next_url)
        return redirect("secretariat:fee-approvals")


class FeeAmountChangeDetailView(SecretariatViewMixin, DetailView):
    model = FeeAmountChangeRequest
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "change"
    template_name = "secretariat/fee_approvals/amount_change_detail.html"

    def get_queryset(self):
        year = self.require_selected_year()
        return (
            FeeAmountChangeRequest.objects.filter(fee__academic_year=year)
            .select_related(
                "fee",
                "fee__category",
                "fee__academic_year",
                "origin_class",
                "requested_by",
                "reviewed_by",
            )
            .prefetch_related("target_classes")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_academic_year()
        change = self.object
        context.update(
            year_writable=bool(year and not year.is_closed),
            can_decide=change.status == FeeAmountChangeRequest.Status.PENDING
            and year
            and not year.is_closed,
            period_label=fee_period_short_label(change.fee),
            target_classes=resolve_change_target_classes(request=change),
            breadcrumbs=[
                ("Secrétariat", reverse("secretariat:dashboard")),
                ("Validation des frais", reverse("secretariat:fee-approvals")),
                (f"Montant — {fee_period_short_label(change.fee)}", None),
            ],
        )
        return context


class FeeAmountChangeApproveView(SecretariatViewMixin, View):
    def post(self, request, public_id):
        change = get_object_or_404(
            FeeAmountChangeRequest,
            public_id=public_id,
            fee__academic_year=self.require_selected_year(),
        )
        try:
            self.require_writable_academic_year()
            require_password(request)
            approve_amount_change(
                change=change,
                actor=request.user,
                request=request,
                comment=request.POST.get("comment", ""),
            )
            messages.success(request, "Modification de montant approuvée.")
        except (FinanceError, SecretariatError) as exc:
            messages.error(request, _action_error_message(exc))
        next_url = request.POST.get("next") or ""
        if next_url.startswith("/"):
            return redirect(next_url)
        return redirect("secretariat:fee-approvals")


class FeeAmountChangeRejectView(SecretariatViewMixin, View):
    def post(self, request, public_id):
        change = get_object_or_404(
            FeeAmountChangeRequest,
            public_id=public_id,
            fee__academic_year=self.require_selected_year(),
        )
        try:
            self.require_writable_academic_year()
            require_password(request)
            reject_amount_change(
                change=change,
                reason=request.POST.get("rejection_reason", ""),
                actor=request.user,
                request=request,
            )
            messages.success(request, "Modification de montant rejetée.")
        except (FinanceError, SecretariatError) as exc:
            messages.error(request, _action_error_message(exc))
        next_url = request.POST.get("next") or ""
        if next_url.startswith("/"):
            return redirect(next_url)
        return redirect("secretariat:fee-approvals")
