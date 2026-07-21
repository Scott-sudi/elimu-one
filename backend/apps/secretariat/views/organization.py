"""Academic organization hub."""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.forms import OptionForm, SchoolLevelForm, SectionForm
from apps.secretariat.models import Option, SchoolLevel, Section
from apps.secretariat.services import academic_service
from apps.secretariat.services.exceptions import SecretariatError


class OrganizationView(SecretaryRequiredMixin, TemplateView):
    template_name = "secretariat/organization/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            levels=SchoolLevel.objects.all(),
            sections=Section.objects.all(),
            options=Option.objects.select_related("section"),
            level_form=SchoolLevelForm(),
            section_form=SectionForm(),
            option_form=OptionForm(),
            active_tab=self.kwargs.get("tab", "levels"),
            breadcrumbs=[("Secrétariat", reverse("secretariat:dashboard")), ("Organisation", None)],
        )
        return context

    def post(self, request, *args, **kwargs):
        kind = request.POST.get("kind")
        mapping = {
            "level": (SchoolLevelForm, academic_service.create_level),
            "section": (SectionForm, academic_service.create_section),
            "option": (OptionForm, academic_service.create_option),
        }
        form_class, service = mapping.get(kind, (None, None))
        if not form_class:
            messages.error(request, "Type d'élément invalide.")
            return redirect("secretariat:organization")
        form = form_class(request.POST)
        if form.is_valid():
            try:
                service(actor=request.user, request=request, **form.cleaned_data)
                messages.success(request, "Élément créé avec succès.")
            except SecretariatError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")
        return redirect("secretariat:organization")
