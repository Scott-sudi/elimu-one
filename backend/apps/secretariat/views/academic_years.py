"""Academic year views."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import FormView

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.forms import AcademicYearForm
from apps.secretariat.models import AcademicYear
from apps.secretariat.services import academic_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView, ServiceFormMixin


class AcademicYearListView(SecretariatListView):
    model = AcademicYear
    template_name = "secretariat/academic_years/list.html"
    partial_template_name = "secretariat/academic_years/_table.html"
    context_object_name = "years"
    page_title = "Années scolaires"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AcademicYearForm()
        return context


class AcademicYearCreateView(SecretaryRequiredMixin, ServiceFormMixin, FormView):
    form_class = AcademicYearForm
    template_name = "secretariat/academic_years/_form.html"
    success_url_name = "secretariat:academic-years"
    success_message = "Année scolaire créée."

    def execute_service(self, form):
        return academic_service.create_academic_year(actor=self.request.user, request=self.request, **form.cleaned_data)


class AcademicYearActionView(SecretaryRequiredMixin, View):
    action = ""

    def post(self, request, public_id):
        year = get_object_or_404(AcademicYear, public_id=public_id)
        try:
            if self.action == "activate":
                academic_service.activate_academic_year(year, actor=request.user, request=request)
                messages.success(request, "Année scolaire activée.")
            else:
                academic_service.close_academic_year(year, actor=request.user, request=request)
                messages.success(request, "Année scolaire clôturée.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:academic-years")
