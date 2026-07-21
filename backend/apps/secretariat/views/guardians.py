"""Guardian views."""

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DetailView

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.forms import GuardianForm
from apps.secretariat.models import Guardian
from apps.secretariat.services import guardian_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView


class GuardianListView(SecretariatListView):
    template_name = "secretariat/guardians/list.html"
    partial_template_name = "secretariat/guardians/_table.html"
    context_object_name = "guardians"
    page_title = "Responsables"

    def get_queryset(self):
        qs = Guardian.objects.annotate(students_count=Count("student_links"))
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nom__icontains=q) | Q(postnom__icontains=q) | Q(prenom__icontains=q)
                | Q(telephone_principal__icontains=q) | Q(email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = GuardianForm()
        return context

    def post(self, request, *args, **kwargs):
        form = GuardianForm(request.POST)
        if form.is_valid():
            try:
                guardian_service.create_guardian(
                    actor=request.user, request=request, **form.cleaned_data
                )
                messages.success(request, "Responsable créé.")
            except SecretariatError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")
        return redirect("secretariat:guardians")


class GuardianDetailView(SecretaryRequiredMixin, DetailView):
    model = Guardian
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "guardian"
    template_name = "secretariat/guardians/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            student_links=self.object.student_links.select_related("student"),
            breadcrumbs=[("Secrétariat", reverse("secretariat:dashboard")), ("Responsables", reverse("secretariat:guardians")), (str(self.object), None)],
        )
        return context
