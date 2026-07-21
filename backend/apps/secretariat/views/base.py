"""Shared secretariat view helpers."""

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.services.exceptions import SecretariatError


class SecretariatListView(SecretaryRequiredMixin, ListView):
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
