"""Academic organization hub."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.secretariat.forms import OptionForm, SchoolLevelForm, SectionForm
from apps.secretariat.models import Option, SchoolLevel, Section
from apps.secretariat.services import academic_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatViewMixin


class OrganizationView(SecretariatViewMixin, TemplateView):
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
            year_writable=self.selected_year_is_writable(),
        )
        return context

    def post(self, request, *args, **kwargs):
        try:
            self.require_writable_academic_year()
        except SecretariatError as exc:
            messages.error(request, str(exc))
            return redirect("secretariat:organization")
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
        tab_map = {"level": "levels", "section": "sections", "option": "options"}
        return redirect(reverse(f"secretariat:{tab_map.get(kind, 'organization')}"))


class _OrganizationEntityMixin(SecretariatViewMixin, View):
    model = None
    form_class = None
    update_service = None
    deactivate_service = None
    reactivate_service = None
    delete_service = None
    redirect_name = "secretariat:organization"
    entity_label = "Élément"

    def get_object(self):
        return get_object_or_404(self.model, public_id=self.kwargs["public_id"])

    def _redirect(self):
        return redirect(self.redirect_name)

    def post(self, request, *args, **kwargs):
        action = getattr(self, "action", request.POST.get("action", "update"))
        obj = self.get_object()
        try:
            self.require_writable_academic_year()
        except SecretariatError as exc:
            messages.error(request, str(exc))
            return self._redirect()
        try:
            if action == "update":
                form = self.form_class(request.POST, instance=obj)
                if not form.is_valid():
                    messages.error(request, "Veuillez corriger les erreurs du formulaire.")
                    return self._redirect()
                self.update_service(obj, actor=request.user, request=request, **form.cleaned_data)
                messages.success(request, f"{self.entity_label} modifié(e).")
            elif action == "deactivate":
                self.deactivate_service(obj, actor=request.user, request=request)
                messages.success(request, f"{self.entity_label} désactivé(e).")
            elif action == "reactivate":
                self.reactivate_service(obj, actor=request.user, request=request)
                messages.success(request, f"{self.entity_label} réactivé(e).")
            elif action == "delete":
                self.delete_service(obj, actor=request.user, request=request)
                messages.success(request, f"{self.entity_label} supprimé(e).")
            else:
                messages.error(request, "Action invalide.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return self._redirect()


class LevelActionView(_OrganizationEntityMixin):
    model = SchoolLevel
    form_class = SchoolLevelForm
    update_service = staticmethod(academic_service.update_level)
    deactivate_service = staticmethod(academic_service.deactivate_level)
    reactivate_service = staticmethod(academic_service.reactivate_level)
    delete_service = staticmethod(academic_service.delete_level)
    redirect_name = "secretariat:levels"
    entity_label = "Niveau"


class SectionActionView(_OrganizationEntityMixin):
    model = Section
    form_class = SectionForm
    update_service = staticmethod(academic_service.update_section)
    deactivate_service = staticmethod(academic_service.deactivate_section)
    reactivate_service = staticmethod(academic_service.reactivate_section)
    delete_service = staticmethod(academic_service.delete_section)
    redirect_name = "secretariat:sections"
    entity_label = "Section"


class OptionActionView(_OrganizationEntityMixin):
    model = Option
    form_class = OptionForm
    update_service = staticmethod(academic_service.update_option)
    deactivate_service = staticmethod(academic_service.deactivate_option)
    reactivate_service = staticmethod(academic_service.reactivate_option)
    delete_service = staticmethod(academic_service.delete_option)
    redirect_name = "secretariat:options"
    entity_label = "Option"
