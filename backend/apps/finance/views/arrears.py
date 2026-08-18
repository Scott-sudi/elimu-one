"""Arrears list view with rich filters."""

from django.db.models import Q

from apps.finance.services.list_filters import list_filter_context, resolve_fee_filter_ids
from apps.finance.services.situation_service import arrears_queryset

from .base import FinanceListView


class ArrearsListView(FinanceListView):
    template_name = "finance/arrears/list.html"
    partial_template_name = "finance/arrears/_table.html"
    context_object_name = "arrears"
    page_title = "Impayés"
    paginate_by = 40

    def get_queryset(self):
        year = self.require_selected_year()
        qs = arrears_queryset(academic_year=year)

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
            qs = qs.filter(fee_id__in=fee_ids)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(student__matricule__icontains=q)
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
