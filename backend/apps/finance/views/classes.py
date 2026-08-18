"""Class situation views for finance."""

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.finance.forms import ClassOtherFeeForm, FeeAmountChangeForm
from apps.finance.models import FeeAmountChangeRequest, SchoolFee
from apps.finance.services.class_fee_request_service import (
    create_and_submit_class_fee_schedule,
)
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.fee_amount_change_service import (
    effective_fee_amount,
    submit_amount_change,
)
from apps.finance.services.fee_structure_service import (
    BOARD_CHOICES,
    BOARD_MINERVAL,
    custom_fee_groups_for_class,
)
from apps.finance.services.payment_sequence_service import fee_period_short_label
from apps.finance.services.situation_service import class_situation_matrix
from apps.secretariat.models import Enrollment, SchoolClass

from .base import FinanceListView, FinanceViewMixin


class ClassListView(FinanceListView):
    template_name = "finance/classes/list.html"
    partial_template_name = "finance/classes/_table.html"
    context_object_name = "classes"
    page_title = "Classes"
    paginate_by = 48

    def get_queryset(self):
        year = self.require_selected_year()
        qs = (
            SchoolClass.objects.filter(academic_year=year, is_active=True)
            .select_related("level", "section", "option")
            .annotate(
                occupied=Count(
                    "enrollments",
                    filter=Q(enrollments__status=Enrollment.Status.VALIDATED),
                )
            )
            .order_by("level__order", "name")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_filters"] = {"q": self.request.GET.get("q", "")}
        return context


class ClassSituationView(FinanceViewMixin, TemplateView):
    template_name = "finance/classes/situation.html"

    def get_school_class(self) -> SchoolClass:
        year = self.require_selected_year()
        return get_object_or_404(
            SchoolClass.objects.select_related(
                "academic_year", "level", "section", "option"
            ),
            public_id=self.kwargs["public_id"],
            academic_year=year,
        )

    def resolve_board(self, school_class: SchoolClass, custom_groups: list[dict]):
        from apps.finance.services.fee_service import fee_applies_to_class
        from apps.finance.services.fee_structure_service import (
            BOARD_ETAT,
            fees_for_board,
        )

        raw = (self.request.GET.get("tableau") or "").strip()
        groups_by_key = {g["key"]: g for g in custom_groups}

        if raw in {BOARD_MINERVAL, "minerval"}:
            fees = [
                fee
                for fee in fees_for_board(
                    academic_year=school_class.academic_year,
                    board=BOARD_MINERVAL,
                )
                if fee_applies_to_class(fee, school_class)
            ]
            return BOARD_MINERVAL, None, fees

        if raw in {BOARD_ETAT, "etat"}:
            fees = [
                fee
                for fee in fees_for_board(
                    academic_year=school_class.academic_year,
                    board=BOARD_ETAT,
                )
                if fee_applies_to_class(fee, school_class)
            ]
            return BOARD_ETAT, None, fees

        if raw in BOARD_CHOICES and raw not in {BOARD_MINERVAL, BOARD_ETAT}:
            raw = ""

        if raw:
            group_key = raw.removeprefix("fee:") if raw.startswith("fee:") else raw
            group_key = group_key.upper()
            group = groups_by_key.get(group_key)
            if group is not None:
                return f"fee:{group['key']}", group, group["fees"]

        if custom_groups:
            group = custom_groups[0]
            return f"fee:{group['key']}", group, group["fees"]

        return "", None, []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_class = self.get_school_class()
        year = school_class.academic_year

        custom_groups = custom_fee_groups_for_class(school_class=school_class)
        board, selected_group, board_fees = self.resolve_board(
            school_class, custom_groups
        )
        matrix = class_situation_matrix(
            school_class=school_class,
            fees=board_fees,
        )
        fee_ids = [fee.pk for fee in matrix["fees"]]
        pending_amount_fee_ids = set(
            FeeAmountChangeRequest.objects.filter(
                fee_id__in=fee_ids,
                status=FeeAmountChangeRequest.Status.PENDING,
            ).values_list("fee_id", flat=True)
        )
        fee_columns = []
        for fee in matrix["fees"]:
            amount_value = effective_fee_amount(fee=fee, school_class=school_class)
            amount = f"{amount_value:,.0f}".replace(",", " ")
            period_label = fee_period_short_label(fee)
            fee_columns.append(
                {
                    "fee": fee,
                    "period_label": period_label,
                    "amount_value": amount_value,
                    "header": f"{period_label} — {amount}",
                    "pending_change": fee.pk in pending_amount_fee_ids,
                }
            )

        pending_qs = (
            SchoolFee.objects.filter(
                academic_year=year,
                status=SchoolFee.Status.PENDING,
                is_active=True,
                targets__school_class=school_class,
            )
            .values("group_key", "label")
            .distinct()
            .order_by("group_key")
        )
        pending_labels = []
        seen = set()
        for row in pending_qs:
            key = (row["group_key"] or "").upper()
            if key in seen:
                continue
            seen.add(key)
            base = (row["label"] or "").split(" — ")[0].strip() or key
            pending_labels.append(base)

        year_classes = list(
            SchoolClass.objects.filter(academic_year=year, is_active=True)
            .select_related("level")
            .order_by("level__order", "name")
        )

        context.update(
            school_class=school_class,
            matrix=matrix,
            fee_columns=fee_columns,
            board=board,
            board_choices=BOARD_CHOICES,
            custom_fee_tabs=custom_groups,
            selected_custom_group=selected_group,
            pending_custom_fees=pending_labels,
            other_fee_form=ClassOtherFeeForm(academic_year=year),
            amount_change_form=FeeAmountChangeForm(academic_year=year),
            year_classes=year_classes,
            year_writable=bool(year and not year.is_closed),
            breadcrumbs=[
                ("Comptabilité", reverse("finance:dashboard")),
                ("Classes", reverse("finance:classes")),
                (school_class.name, None),
            ],
        )
        return context


class ClassFeeAmountChangeView(FinanceViewMixin, View):
    """Submit a fee period amount change request to the secretariat."""

    def _redirect(self, public_id, board: str = ""):
        url = reverse("finance:class-situation", kwargs={"public_id": public_id})
        board = (board or "").strip()
        if board and board not in {BOARD_MINERVAL, "etat"}:
            url += f"?tableau={board}"
        return redirect(url)

    def post(self, request, public_id):
        year = self.require_selected_year()
        board = (request.POST.get("tableau") or "").strip()
        try:
            self.require_writable_academic_year()
        except FinanceError as exc:
            messages.error(request, str(exc))
            return self._redirect(public_id, board)

        school_class = get_object_or_404(
            SchoolClass.objects.select_related("academic_year"),
            public_id=public_id,
            academic_year=year,
        )
        form = FeeAmountChangeForm(request.POST, academic_year=year)
        if not form.is_valid():
            messages.error(
                request,
                "Vérifiez le montant, la portée et les classes sélectionnées.",
            )
            return self._redirect(public_id, board)

        data = form.cleaned_data
        fee = get_object_or_404(
            SchoolFee,
            public_id=data["fee_id"],
            academic_year=year,
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
        )
        try:
            change = submit_amount_change(
                fee=fee,
                origin_class=school_class,
                new_amount=data["new_amount"],
                scope=data["scope"],
                target_classes=list(data.get("target_classes") or []),
                comment=data.get("comment") or "",
                actor=request.user,
                request=request,
            )
        except FinanceError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                f"Modification de « {fee_period_short_label(fee)} » "
                f"({change.new_amount}) envoyée au secrétariat.",
            )
        return self._redirect(public_id, board)


class ClassOtherFeeCreateView(FinanceViewMixin, View):
    """Create a scheduled class fee and submit it to the secretariat."""

    def _redirect(self, public_id, group_key: str = ""):
        url = reverse("finance:class-situation", kwargs={"public_id": public_id})
        key = (group_key or "").strip().upper()
        if key:
            url += f"?tableau=fee:{key}"
        return redirect(url)

    def post(self, request, public_id):
        year = self.require_selected_year()
        try:
            self.require_writable_academic_year()
        except FinanceError as exc:
            messages.error(request, str(exc))
            return self._redirect(public_id)

        school_class = get_object_or_404(
            SchoolClass,
            public_id=public_id,
            academic_year=year,
        )
        form = ClassOtherFeeForm(request.POST, academic_year=year)
        if not form.is_valid():
            messages.error(
                request,
                "Vérifiez le code, le nom, le montant, le motif et le mode de paiement.",
            )
            return self._redirect(public_id)

        data = form.cleaned_data
        group_key = (data.get("code") or "").strip().upper()
        try:
            created = create_and_submit_class_fee_schedule(
                academic_year=year,
                school_class=school_class,
                code=data["code"],
                label=data["label"],
                amount=data["amount"],
                description=data["description"],
                schedule_mode=data["schedule_mode"],
                tranche_count=data.get("tranche_count") or 1,
                month_scope=data.get("month_scope") or "TOUS",
                month_keys=list(data.get("months") or []),
                actor=request.user,
                request=request,
            )
        except FinanceError as exc:
            messages.error(request, str(exc))
            return self._redirect(public_id)
        messages.success(
            request,
            f"Frais « {data['label']} » ({len(created)} colonne(s)) envoyé au "
            "secrétariat. L'onglet apparaîtra après validation.",
        )
        return self._redirect(public_id, group_key)
