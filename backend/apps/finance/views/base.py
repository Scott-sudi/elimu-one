"""Shared finance view helpers."""

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView

from apps.core.mixins import AccountantRequiredMixin
from apps.finance.services.exceptions import FinanceError
from apps.secretariat.services.exceptions import SecretariatError
from apps.secretariat.services.year_context import year_context_service


class FinanceAcademicYearRequiredMixin:
    """Redirect accountants to the year picker when none is selected."""

    academic_year_required = True

    def dispatch(self, request, *args, **kwargs):
        if self.academic_year_required and getattr(request.user, "is_authenticated", False):
            if not year_context_service.has_session_year(request):
                messages.info(
                    request,
                    "Choisissez une année scolaire avant d'accéder à la comptabilité.",
                )
                return redirect("secretariat:academic-year-select")
        return super().dispatch(request, *args, **kwargs)

    def get_selected_academic_year(self):
        return year_context_service.get_selected_year(self.request)

    def require_selected_year(self):
        """Year must be selected (closed years remain readable only)."""
        try:
            return year_context_service.require_selected_year(self.request)
        except SecretariatError as exc:
            raise FinanceError(str(exc)) from exc

    def require_writable_academic_year(self):
        """Selected year must be open — blocks modifications on a closed year."""
        year = self.require_selected_year()
        if year.is_closed:
            raise FinanceError(
                "Cette année scolaire est clôturée. Consultation uniquement — "
                "aucune modification n'est possible."
            )
        return year


class FinanceViewMixin(AccountantRequiredMixin, FinanceAcademicYearRequiredMixin):
    """Standard access gate for finance business pages (role, then year)."""


class FinanceListView(FinanceViewMixin, ListView):
    paginate_by = 25
    partial_template_name = ""
    page_title = ""

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true" and self.partial_template_name:
            return [self.partial_template_name]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            ("Comptabilité", reverse("finance:dashboard")),
            (self.page_title, None),
        ]
        year = self.get_selected_academic_year()
        context["year_writable"] = bool(year and not year.is_closed)
        return context


class ServiceFormMixin:
    success_url_name = ""
    success_message = "Opération effectuée avec succès."

    def execute_service(self, form):
        raise NotImplementedError

    def form_valid(self, form):
        try:
            self.object = self.execute_service(form)
        except FinanceError as exc:
            form.add_error(None, str(exc))
            messages.error(self.request, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(self.success_url_name)
