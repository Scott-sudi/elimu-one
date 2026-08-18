"""Secretariat academic-year selection views."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import YearOperatorRequiredMixin
from apps.secretariat.models import AcademicYear
from apps.secretariat.services.year_context import ordered_academic_years, year_context_service


def _home_after_year_select(user):
    if getattr(user, "is_comptable", lambda: False)():
        return "finance:dashboard"
    if getattr(user, "has_role", lambda *_: False)("DISCIPLINE"):
        return "discipline:dashboard"
    if getattr(user, "is_prefet", lambda: False)():
        return "bi:overview"
    return "secretariat:dashboard"


def _year_select_module_label(user) -> str:
    if getattr(user, "is_comptable", lambda: False)():
        return "Comptabilité"
    if getattr(user, "has_role", lambda *_: False)("DISCIPLINE"):
        return "Discipline"
    if getattr(user, "is_prefet", lambda: False)():
        return "Business Intelligence"
    return "Secrétariat"


class AcademicYearSelectView(YearOperatorRequiredMixin, TemplateView):
    """Mandatory year picker for secrétaire and comptable."""

    template_name = "secretariat/academic_years/select.html"
    academic_year_required = False

    def get_context_data(self, **kwargs):
        from apps.secretariat.services.academic_service import (
            can_create_academic_year,
            get_open_current_year,
        )

        context = super().get_context_data(**kwargs)
        years = list(ordered_academic_years())
        blocking = get_open_current_year()
        module = _year_select_module_label(self.request.user)
        context.update(
            academic_years=years,
            selected_year=year_context_service.get_selected_year(self.request),
            has_years=bool(years),
            can_create_year=self.request.user.is_secretaire() and can_create_academic_year(),
            blocking_year=blocking,
            breadcrumbs=[(module, None), ("Choisir une année scolaire", None)],
        )
        return context


class AcademicYearChooseView(YearOperatorRequiredMixin, View):
    """Persist the chosen academic year in the Django session."""

    academic_year_required = False

    def post(self, request, public_id):
        year = get_object_or_404(AcademicYear, public_id=public_id)
        year_context_service.select_year(request, year, actor=request.user)
        messages.success(
            request,
            f"Vous travaillez maintenant sur l'année scolaire {year.label}.",
        )
        return redirect(_home_after_year_select(request.user))


class AcademicYearChangeView(YearOperatorRequiredMixin, View):
    """Clear selection and return to the year picker."""

    academic_year_required = False

    def get(self, request):
        return redirect("secretariat:academic-year-select")

    def post(self, request):
        year_context_service.clear_selected_year(request)
        messages.info(request, "Sélectionnez une année scolaire pour continuer.")
        return redirect("secretariat:academic-year-select")
