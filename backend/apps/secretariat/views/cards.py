"""Student card views."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.models import Enrollment, StudentCard
from apps.secretariat.services import card_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView


class CardListView(SecretariatListView):
    template_name = "secretariat/cards/list.html"
    partial_template_name = "secretariat/cards/_table.html"
    context_object_name = "cards"
    page_title = "Cartes d'élèves"

    def get_queryset(self):
        return StudentCard.objects.select_related("student", "enrollment__school_class")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["eligible_enrollments"] = Enrollment.objects.filter(
            status=Enrollment.Status.VALIDATED, cards__isnull=True
        ).select_related("student", "school_class")
        return context


class CardPreviewView(SecretaryRequiredMixin, DetailView):
    model = StudentCard
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "card"
    template_name = "secretariat/cards/preview.html"


class CardGenerateView(SecretaryRequiredMixin, View):
    def post(self, request, public_id):
        enrollment = get_object_or_404(Enrollment, public_id=public_id)
        try:
            card_service.generate_card(enrollment=enrollment, actor=request.user, request=request)
            messages.success(request, "Carte générée.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:cards")


class CardBlockView(SecretaryRequiredMixin, View):
    def post(self, request, public_id):
        card = get_object_or_404(StudentCard, public_id=public_id)
        try:
            card_service.block_card(card, reason=request.POST.get("reason", ""), actor=request.user, request=request)
            messages.success(request, "Carte bloquée.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:cards")
