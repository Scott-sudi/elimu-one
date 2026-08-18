"""Academic year views."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView

from apps.secretariat.forms import AcademicYearForm
from apps.secretariat.models import AcademicYear
from apps.secretariat.services import academic_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView, SecretariatViewMixin, ServiceFormMixin


class AcademicYearListView(SecretariatListView):
    model = AcademicYear
    template_name = "secretariat/academic_years/list.html"
    partial_template_name = "secretariat/academic_years/_table.html"
    context_object_name = "years"
    page_title = "Années scolaires"
    academic_year_required = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AcademicYearForm()
        context["can_create_year"] = academic_service.can_create_academic_year()
        context["blocking_year"] = academic_service.get_open_current_year()
        context["open_create_modal"] = (
            self.request.GET.get("nouvelle") == "1" and context["can_create_year"]
        )
        return context


class AcademicYearCreateView(SecretariatViewMixin, ServiceFormMixin, FormView):
    form_class = AcademicYearForm
    template_name = "secretariat/academic_years/_form.html"
    success_url_name = "secretariat:academic-years"
    success_message = "Année scolaire créée."
    academic_year_required = False

    def execute_service(self, form):
        return academic_service.create_academic_year(
            actor=self.request.user, request=self.request, **form.cleaned_data
        )


class AcademicYearUpdateView(SecretariatViewMixin, ServiceFormMixin, FormView):
    form_class = AcademicYearForm
    template_name = "secretariat/academic_years/update.html"
    success_message = "Année scolaire modifiée."
    academic_year_required = False

    def dispatch(self, request, *args, **kwargs):
        self.year = get_object_or_404(AcademicYear, public_id=kwargs["public_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.year
        return kwargs

    def execute_service(self, form):
        return academic_service.update_academic_year(
            self.year, actor=self.request.user, request=self.request, **form.cleaned_data
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["year"] = self.year
        context["breadcrumbs"] = [
            ("Secrétariat", reverse("secretariat:dashboard")),
            ("Années scolaires", reverse("secretariat:academic-years")),
            (self.year.label, None),
        ]
        return context

    def get_success_url(self):
        return reverse("secretariat:academic-years")


class AcademicYearDeleteView(SecretariatViewMixin, View):
    academic_year_required = False

    def post(self, request, public_id):
        year = get_object_or_404(AcademicYear, public_id=public_id)
        try:
            academic_service.delete_academic_year(year, actor=request.user, request=request)
            messages.success(request, "Année scolaire supprimée.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:academic-years")


class AcademicYearActionView(SecretariatViewMixin, View):
    action = ""
    academic_year_required = False

    def post(self, request, public_id):
        year = get_object_or_404(AcademicYear, public_id=public_id)
        try:
            if self.action == "activate":
                academic_service.activate_academic_year(
                    year, actor=request.user, request=request
                )
                messages.success(request, "Année scolaire activée.")
            else:
                academic_service.close_academic_year(
                    year,
                    closure_notes=request.POST.get("closure_notes", ""),
                    actor=request.user,
                    request=request,
                )
                messages.success(
                    request,
                    "Année scolaire clôturée. Les cartes d'élèves de cette année sont bloquées.",
                )
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:academic-years")


class AcademicYearDeclareCloseView(SecretariatViewMixin, View):
    """Close the currently selected academic year from the hamburger menu modal."""

    def post(self, request):
        try:
            year = self.get_selected_academic_year()
            if year is None:
                raise SecretariatError("Aucune année scolaire n'est sélectionnée.")
            notes = request.POST.get("closure_notes", "").strip()
            if not notes:
                raise SecretariatError("Ajoutez une observation ou un bilan de l'année avant de clôturer.")
            password = request.POST.get("password", "")
            if not password:
                raise SecretariatError("Saisissez votre mot de passe pour confirmer la clôture.")
            if not request.user.check_password(password):
                raise SecretariatError("Mot de passe incorrect. La clôture a été annulée.")
            academic_service.close_academic_year(
                year,
                closure_notes=notes,
                actor=request.user,
                request=request,
            )
            from apps.secretariat.services.year_context import year_context_service

            year_context_service.clear_selected_year(request)
            messages.success(
                request,
                f"L'année scolaire {year.label} a été clôturée. "
                "Les cartes d'élèves de cette année sont bloquées. "
                "Choisissez ou créez la prochaine année.",
            )
            return redirect("secretariat:academic-year-select")
        except SecretariatError as exc:
            messages.error(request, str(exc))
            return redirect(request.META.get("HTTP_REFERER") or "secretariat:dashboard")
