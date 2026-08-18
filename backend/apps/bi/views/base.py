"""Shared BI view helpers — Préfet read-only, year required (closed years allowed)."""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from apps.core.mixins import PrefetRequiredMixin
from apps.secretariat.models import SchoolClass
from apps.secretariat.services.exceptions import SecretariatError
from apps.secretariat.services.year_context import year_context_service


class BiAcademicYearRequiredMixin:
    """Redirect prefets to the year picker when none is selected.

    Closed years remain fully readable — no writable gate for BI.
    """

    academic_year_required = True

    def dispatch(self, request, *args, **kwargs):
        if self.academic_year_required and getattr(request.user, "is_authenticated", False):
            if not year_context_service.has_session_year(request):
                messages.info(
                    request,
                    "Choisissez une année scolaire avant d'accéder à la Business Intelligence.",
                )
                return redirect("secretariat:academic-year-select")
        return super().dispatch(request, *args, **kwargs)

    def get_selected_academic_year(self):
        return year_context_service.get_selected_year(self.request)

    def require_selected_year(self):
        """Year must be selected — closed years remain readable."""
        try:
            return year_context_service.require_selected_year(self.request)
        except SecretariatError as exc:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(str(exc)) from exc


class BiViewMixin(PrefetRequiredMixin, BiAcademicYearRequiredMixin):
    """Standard access gate for BI pages (role Préfet, then year)."""


class BiPageView(BiViewMixin, TemplateView):
    """Routed BI page shell."""

    template_name = "bi/overview/index.html"
    page_title = "Business Intelligence"
    breadcrumb_tail = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        classes = SchoolClass.objects.filter(
            academic_year=year,
            is_active=True,
        ).select_related("section", "option").order_by("name")
        context.update(
            page_title=self.page_title,
            selected_year=year,
            bi_classes=classes,
            bi_sections=classes.values_list("section_id", "section__name").distinct().order_by("section__name"),
            bi_options=classes.values_list("option_id", "option__name").distinct().order_by("option__name"),
            breadcrumbs=[
                ("Business Intelligence", reverse("bi:overview")),
                (self.breadcrumb_tail or self.page_title, None),
            ],
        )
        return context
