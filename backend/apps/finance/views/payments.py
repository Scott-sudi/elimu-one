"""Payment views."""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView

from apps.finance.forms import PaymentForm
from apps.finance.models import Payment, StudentFeeObligation
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.fee_structure_service import payable_fees_for_class
from apps.finance.services.list_filters import list_filter_context, resolve_fee_filter_ids
from apps.finance.services.matricule_lookup import (
    class_matricule_stem,
    find_enrollment_by_matricule_suffix,
    matricule_stem,
)
from apps.finance.services.payment_sequence_service import (
    build_payable_fee_groups,
    build_payable_fee_groups_for_enrollment,
    fee_period_short_label,
    resolve_sequential_obligation,
)
from apps.finance.services.password import require_password
from apps.finance.services.payment_service import cancel_payment, record_payment
from apps.secretariat.models import Enrollment, SchoolClass

from .base import FinanceListView, FinanceViewMixin, ServiceFormMixin


class PaymentListView(FinanceListView):
    template_name = "finance/payments/list.html"
    partial_template_name = "finance/payments/_table.html"
    context_object_name = "payments"
    page_title = "Paiements"
    paginate_by = 40

    def get_queryset(self):
        year = self.require_selected_year()
        qs = (
            Payment.objects.filter(academic_year=year)
            .select_related(
                "student",
                "enrollment",
                "enrollment__school_class",
                "recorded_by",
            )
            .prefetch_related("allocations__obligation")
            .order_by("-payment_date", "-created_at")
        )

        option_id = self.request.GET.get("option", "").strip()
        if option_id:
            qs = qs.filter(enrollment__school_class__option__public_id=option_id)

        niveau_id = self.request.GET.get("niveau", "").strip()
        if niveau_id:
            qs = qs.filter(enrollment__school_class__level__public_id=niveau_id)

        fee_ids = resolve_fee_filter_ids(
            year=year,
            frais=self.request.GET.get("frais", ""),
            periode=self.request.GET.get("periode", ""),
        )
        if fee_ids is not None:
            qs = qs.filter(allocations__obligation__fee_id__in=fee_ids).distinct()

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(receipt_number__icontains=q)
                | Q(student__matricule__icontains=q)
                | Q(student__nom__icontains=q)
                | Q(student__postnom__icontains=q)
                | Q(student__prenom__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        context.update(list_filter_context(self.request, year=year))
        return context


class PaymentCreateView(FinanceViewMixin, ServiceFormMixin, FormView):
    form_class = PaymentForm
    template_name = "finance/payments/create.html"
    success_message = "Paiement enregistré."

    def dispatch(self, request, *args, **kwargs):
        try:
            self.require_writable_academic_year()
        except FinanceError as exc:
            messages.error(request, str(exc))
            return redirect("finance:payments")
        self.school_class = None
        year = self.require_selected_year()
        class_id = request.GET.get("classe") or request.POST.get("classe")
        if class_id:
            self.school_class = get_object_or_404(
                SchoolClass.objects.select_related("academic_year"),
                public_id=class_id,
                academic_year=year,
            )
        return super().dispatch(request, *args, **kwargs)

    def resolve_enrollment_from_request(self):
        """Enrollment from POST/GET matricule suffix when available."""
        year = self.require_selected_year()
        suffix = ""
        if self.request.method == "POST":
            suffix = (self.request.POST.get("matricule_suffix") or "").strip()
        if not suffix:
            return None
        try:
            return find_enrollment_by_matricule_suffix(
                suffix=suffix,
                academic_year=year,
                school_class=self.school_class,
                stem=self.get_matricule_stem(),
            )
        except Enrollment.DoesNotExist:
            return None

    def get_payable_fees(self):
        """Fees for the class context, or for the student resolved from matricule."""
        year = self.require_selected_year()
        if self.school_class:
            return payable_fees_for_class(school_class=self.school_class)

        suffix = ""
        if self.request.method == "POST":
            suffix = (self.request.POST.get("matricule_suffix") or "").strip()
        if not suffix:
            return []

        try:
            enrollment = find_enrollment_by_matricule_suffix(
                suffix=suffix,
                academic_year=year,
                school_class=None,
                stem=self.get_matricule_stem(),
            )
        except Enrollment.DoesNotExist:
            return []
        return payable_fees_for_class(school_class=enrollment.school_class)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        fees = self.get_payable_fees()
        kwargs["fees"] = fees
        kwargs["enrollment"] = self.resolve_enrollment_from_request()
        return kwargs

    def get_matricule_stem(self) -> str:
        year = self.require_selected_year()
        if self.school_class:
            return class_matricule_stem(school_class=self.school_class)
        return matricule_stem(year=year.start_date.year)

    def execute_service(self, form):
        year = self.require_selected_year()
        stem = self.get_matricule_stem()
        try:
            enrollment = find_enrollment_by_matricule_suffix(
                suffix=form.cleaned_data["matricule_suffix"],
                academic_year=year,
                school_class=self.school_class,
                stem=stem,
            )
        except Enrollment.DoesNotExist as exc:
            raise FinanceError(str(exc)) from exc

        selected_fee = form.cleaned_data["fee"]
        if self.school_class and enrollment.school_class_id != self.school_class.pk:
            raise FinanceError("Cet élève n'appartient pas à la classe sélectionnée.")

        class_fees = payable_fees_for_class(school_class=enrollment.school_class)
        if selected_fee.pk not in {fee.pk for fee in class_fees}:
            raise FinanceError(
                "Ce frais n'est pas applicable à la classe de cet élève."
            )

        obligation, redirected = resolve_sequential_obligation(
            enrollment=enrollment,
            selected_fee=selected_fee,
        )
        remaining = obligation.amount_remaining

        amount = form.cleaned_data.get("amount")
        if amount is None:
            amount = remaining
        else:
            try:
                amount = Decimal(str(amount)).quantize(Decimal("0.01"))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise FinanceError("Montant invalide.") from exc
        if amount <= 0:
            raise FinanceError("Le montant doit être supérieur à zéro.")
        if amount > remaining:
            raise FinanceError(
                f"Impossible de payer {amount} {obligation.fee.currency}. "
                f"Le reste dû pour « {fee_period_short_label(obligation.fee)} » "
                f"est de {remaining} {obligation.fee.currency}."
            )

        payment = record_payment(
            enrollment=enrollment,
            amount_total=amount,
            allocations=[{"obligation": obligation, "amount": amount}],
            currency=obligation.fee.currency or "CDF",
            payment_method=form.cleaned_data["payment_method"],
            actor=self.request.user,
            request=self.request,
        )
        if redirected:
            messages.info(
                self.request,
                "Période antérieure non soldée : le paiement a été enregistré sur "
                f"« {fee_period_short_label(obligation.fee)} ».",
            )
        return payment

    def get_success_url(self):
        return reverse("finance:payment-detail", args=[self.object.public_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        back_url = reverse("finance:payments")
        if self.school_class:
            back_url = reverse(
                "finance:class-situation",
                kwargs={"public_id": self.school_class.public_id},
            )
        fees = self.get_payable_fees()
        enrollment = self.resolve_enrollment_from_request()
        if enrollment:
            fee_groups = build_payable_fee_groups_for_enrollment(
                enrollment=enrollment,
                fees=fees,
            )
        else:
            fee_groups = build_payable_fee_groups(fees)
        fee_groups_payload = [
            {
                "key": g["key"],
                "label": g["label"],
                "schedule_mode": g["schedule_mode"],
                "periods": g["periods"],
            }
            for g in fee_groups
        ]
        context.update(
            school_class=self.school_class,
            matricule_stem=self.get_matricule_stem(),
            payable_fees=fees,
            fee_groups_payload=fee_groups_payload,
            matricule_lookup_url=reverse("finance:payment-matricule-lookup"),
            back_url=back_url,
            breadcrumbs=[
                ("Comptabilité", reverse("finance:dashboard")),
                ("Paiements", reverse("finance:payments")),
                ("Nouveau", None),
            ],
        )
        return context


class PaymentMatriculeLookupView(FinanceViewMixin, View):
    """Resolve matricule → student/class → payable fee groups for the payment form."""

    def get(self, request):
        year = self.require_selected_year()
        suffix = (request.GET.get("suffix") or "").strip()
        stem = (request.GET.get("stem") or "").strip() or None
        class_id = (request.GET.get("classe") or "").strip()
        school_class = None
        if class_id:
            school_class = get_object_or_404(
                SchoolClass.objects.select_related("academic_year"),
                public_id=class_id,
                academic_year=year,
            )
            if not stem:
                stem = class_matricule_stem(school_class=school_class)
        if not stem:
            stem = matricule_stem(year=year.start_date.year)

        if not suffix:
            return JsonResponse(
                {"ok": False, "error": "Saisissez la fin du matricule."},
                status=400,
            )

        try:
            enrollment = find_enrollment_by_matricule_suffix(
                suffix=suffix,
                academic_year=year,
                school_class=school_class,
                stem=stem,
            )
        except Enrollment.DoesNotExist as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=404)

        student = enrollment.student
        full_name = " ".join(
            part
            for part in [student.nom, student.postnom, student.prenom]
            if part
        ).strip()
        fees = payable_fees_for_class(school_class=enrollment.school_class)
        fee_groups = [
            {
                "key": g["key"],
                "label": g["label"],
                "schedule_mode": g["schedule_mode"],
                "periods": g["periods"],
            }
            for g in build_payable_fee_groups_for_enrollment(
                enrollment=enrollment,
                fees=fees,
            )
        ]
        if not fee_groups:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Cet élève n'a plus de frais impayés pour cette année.",
                },
                status=404,
            )
        return JsonResponse(
            {
                "ok": True,
                "student": {
                    "name": full_name,
                    "matricule": student.matricule,
                    "class_name": str(enrollment.school_class),
                    "class_id": str(enrollment.school_class.public_id),
                },
                "fee_groups": fee_groups,
            }
        )


class PaymentDetailView(FinanceViewMixin, DetailView):
    model = Payment
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "payment"
    template_name = "finance/payments/detail.html"

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
                "cancelled_by",
            )
            .prefetch_related("allocations__obligation__fee")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_academic_year()
        payment = self.object
        context.update(
            year_writable=bool(year and not year.is_closed),
            can_cancel=payment.status == Payment.Status.VALID
            and year
            and not year.is_closed,
            breadcrumbs=[
                ("Comptabilité", reverse("finance:dashboard")),
                ("Paiements", reverse("finance:payments")),
                (payment.receipt_number, None),
            ],
        )
        return context


class PaymentCancelView(FinanceViewMixin, View):
    def post(self, request, public_id):
        payment = get_object_or_404(
            Payment,
            public_id=public_id,
            academic_year=self.require_selected_year(),
        )
        try:
            self.require_writable_academic_year()
            require_password(request)
            cancel_payment(
                payment=payment,
                reason=request.POST.get("cancellation_reason", ""),
                actor=request.user,
                request=request,
            )
            messages.success(request, "Paiement annulé.")
        except FinanceError as exc:
            messages.error(request, str(exc))
        return redirect("finance:payment-detail", public_id=public_id)
