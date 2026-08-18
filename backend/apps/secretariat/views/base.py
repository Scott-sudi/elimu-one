"""Shared secretariat view helpers."""

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.services.exceptions import SecretariatError
from apps.secretariat.services.year_context import year_context_service

# URL names that may be accessed without a selected academic year.
ACADEMIC_YEAR_EXEMPT_URL_NAMES = frozenset(
    {
        "academic-year-select",
        "academic-year-choose",
        "academic-year-change",
        "academic-years",
        "academic-year-create",
        "academic-year-activate",
        "academic-year-close",
        "academic-year-update",
        "academic-year-delete",
        # Les responsables ne sont pas liés à une année scolaire.
        "guardians",
        "guardian-detail",
        "guardian-update",
        "guardian-archive",
        "guardian-restore",
    }
)


class SecretariatAcademicYearRequiredMixin:
    """Redirect secretaries to the year picker when none is selected.

    Set ``academic_year_required = False`` on views that must stay reachable
    without a year (picker itself, academic-year admin).
    """

    academic_year_required = True

    def dispatch(self, request, *args, **kwargs):
        if self.academic_year_required and getattr(request.user, "is_authenticated", False):
            url_name = getattr(getattr(request, "resolver_match", None), "url_name", None)
            if url_name not in ACADEMIC_YEAR_EXEMPT_URL_NAMES:
                if not year_context_service.has_session_year(request):
                    messages.info(
                        request,
                        "Choisissez une année scolaire avant d'accéder au secrétariat.",
                    )
                    return redirect("secretariat:academic-year-select")
        return super().dispatch(request, *args, **kwargs)

    def get_selected_academic_year(self):
        return year_context_service.get_selected_year(self.request)

    def selected_year_is_writable(self) -> bool:
        year = self.get_selected_academic_year()
        return bool(year is not None and not year.is_closed)

    def require_selected_year(self):
        """Year must be selected (closed years remain readable only)."""
        return year_context_service.require_selected_year(self.request)

    def require_writable_academic_year(self):
        """Selected year must be open — blocks any modification on a closed year."""
        year = self.require_selected_year()
        if year.is_closed:
            raise SecretariatError(
                "Cette année scolaire est clôturée. Consultation uniquement — "
                "aucune modification n'est possible."
            )
        return year


class SecretariatViewMixin(SecretaryRequiredMixin, SecretariatAcademicYearRequiredMixin):
    """Standard access gate for secretariat business pages (role, then year)."""


class SecretariatListView(SecretariatViewMixin, ListView):
    paginate_by = 25
    partial_template_name = ""

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true" and self.partial_template_name:
            return [self.partial_template_name]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [("Secrétariat", reverse("secretariat:dashboard")), (self.page_title, None)]
        return context


class ServiceFormMixin:
    success_url_name = ""
    success_message = "Opération effectuée avec succès."

    def execute_service(self, form):
        raise NotImplementedError

    def form_valid(self, form):
        try:
            self.object = self.execute_service(form)
        except SecretariatError as exc:
            form.add_error(None, str(exc))
            messages.error(self.request, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(self.success_url_name)
