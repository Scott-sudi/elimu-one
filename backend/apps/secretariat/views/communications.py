"""Communication views."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.forms import CommunicationForm
from apps.secretariat.models import Communication
from apps.secretariat.services import communication_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView


class CommunicationListView(SecretariatListView):
    template_name = "secretariat/communications/list.html"
    partial_template_name = "secretariat/communications/_table.html"
    context_object_name = "communications"
    page_title = "Communications"

    def get_queryset(self):
        qs = Communication.objects.select_related("author")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))
        if self.request.GET.get("status"):
            qs = qs.filter(status=self.request.GET["status"])
        return qs


class CommunicationCreateView(SecretaryRequiredMixin, FormView):
    form_class = CommunicationForm
    template_name = "secretariat/communications/create.html"

    def form_valid(self, form):
        data = form.cleaned_data.copy()
        target_type = data.pop("target_type")
        target = {"target_type": target_type}
        for field in (
            "academic_year", "level", "section", "option",
            "school_class", "student", "guardian",
        ):
            value = data.pop(field, None)
            if value is not None:
                target[field] = value
        try:
            communication = communication_service.create_draft(
                targets=[target],
                actor=self.request.user, request=self.request, **data,
            )
            messages.success(self.request, "Brouillon créé.")
            return redirect("secretariat:communication-detail", public_id=communication.public_id)
        except SecretariatError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)


class CommunicationDetailView(SecretaryRequiredMixin, DetailView):
    model = Communication
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "communication"
    template_name = "secretariat/communications/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [("Secrétariat", reverse("secretariat:dashboard")), ("Communications", reverse("secretariat:communications")), (self.object.title, None)]
        return context


class CommunicationPublishView(SecretaryRequiredMixin, View):
    def post(self, request, public_id):
        communication = get_object_or_404(Communication, public_id=public_id)
        try:
            communication_service.publish(communication, actor=request.user, request=request)
            messages.success(request, "Communication publiée.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:communication-detail", public_id=public_id)
