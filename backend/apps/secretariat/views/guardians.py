"""Guardian views."""

import logging

from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView

from apps.secretariat.forms import GuardianForm
from apps.secretariat.models import Guardian, StudentGuardian
from apps.secretariat.services import guardian_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView, SecretariatViewMixin, ServiceFormMixin

logger = logging.getLogger(__name__)


class GuardianListView(SecretariatListView):
    template_name = "secretariat/guardians/list.html"
    partial_template_name = "secretariat/guardians/_table.html"
    context_object_name = "guardians"
    page_title = "Responsables"
    # Accessible même sans année sélectionnée (dossier parent indépendant).
    academic_year_required = False

    def guardians_writable(self) -> bool:
        """Création/modif OK si pas d'année, ou si l'année sélectionnée est ouverte."""
        year = self.get_selected_academic_year()
        return year is None or not year.is_closed

    def get_queryset(self):
        qs = Guardian.objects.annotate(students_count=Count("student_links")).prefetch_related(
            Prefetch(
                "student_links",
                queryset=StudentGuardian.objects.select_related("student").order_by(
                    "student__nom", "student__prenom"
                ),
            )
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nom__icontains=q)
                | Q(postnom__icontains=q)
                | Q(prenom__icontains=q)
                | Q(telephone_principal__icontains=q)
                | Q(telephone_secondaire__icontains=q)
                | Q(email__icontains=q)
                | Q(numero_identification__icontains=q)
            )
        status = self.request.GET.get("status", "").strip()
        if status == "archived" or status == "ARCHIVE":
            qs = qs.filter(is_archived=True)
        elif status == "inactive":
            qs = qs.filter(is_active=False, is_archived=False)
        elif status == "active":
            qs = qs.filter(is_active=True, is_archived=False)
        else:
            # Default: hide archived unless filtered.
            if status != "all":
                qs = qs.filter(is_archived=False)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = GuardianForm()
        context["year_writable"] = self.guardians_writable()
        return context

    def post(self, request, *args, **kwargs):
        year = self.get_selected_academic_year()
        if year is not None and year.is_closed:
            messages.error(
                request,
                "Cette année scolaire est clôturée. Consultation uniquement — "
                "aucune modification n'est possible.",
            )
            return redirect("secretariat:guardians")
        form = GuardianForm(request.POST)
        if form.is_valid():
            year_start = None
            if year is not None and year.start_date:
                year_start = year.start_date.year
            data = dict(form.cleaned_data)
            data["is_active"] = True
            try:
                guardian = guardian_service.create_guardian(
                    actor=request.user,
                    request=request,
                    academic_year_start=year_start,
                    **data,
                )
                messages.success(
                    request,
                    f"Responsable créé : {guardian} "
                    f"(N° {guardian.numero_identification}).",
                )
            except SecretariatError as exc:
                messages.error(request, str(exc))
            except Exception as exc:
                logger.exception("Échec création responsable")
                messages.error(
                    request,
                    f"Impossible de créer le responsable : {exc}",
                )
        else:
            parts: list[str] = []
            for field, errors in form.errors.items():
                label = field
                if field in form.fields:
                    label = str(form.fields[field].label or field)
                for err in errors:
                    parts.append(f"{label} : {err}")
            messages.error(
                request,
                "Responsable non enregistré. "
                + (" ".join(parts) if parts else "Vérifiez le formulaire."),
            )
        return redirect("secretariat:guardians")


class GuardianDetailView(SecretariatViewMixin, DetailView):
    model = Guardian
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "guardian"
    template_name = "secretariat/guardians/detail.html"
    academic_year_required = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_academic_year()
        context.update(
            student_links=self.object.student_links.select_related("student"),
            year_writable=year is None or not year.is_closed,
            breadcrumbs=[
                ("Secrétariat", reverse("secretariat:dashboard")),
                ("Responsables", reverse("secretariat:guardians")),
                (str(self.object), None),
            ],
        )
        return context


class GuardianUpdateView(SecretariatViewMixin, ServiceFormMixin, FormView):
    form_class = GuardianForm
    template_name = "secretariat/guardians/update.html"
    success_message = "Responsable modifié."
    academic_year_required = False

    def dispatch(self, request, *args, **kwargs):
        self.guardian = get_object_or_404(Guardian, public_id=kwargs["public_id"])
        year = self.get_selected_academic_year()
        if year and year.is_closed:
            messages.error(
                request,
                "Cette année scolaire est clôturée. Consultation uniquement — "
                "aucune modification n'est possible.",
            )
            return redirect("secretariat:guardian-detail", public_id=self.guardian.public_id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.guardian
        return kwargs

    def execute_service(self, form):
        self.require_writable_academic_year()
        return guardian_service.update_guardian(
            self.guardian, actor=self.request.user, request=self.request, **form.cleaned_data
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["guardian"] = self.guardian
        context["breadcrumbs"] = [
            ("Secrétariat", reverse("secretariat:dashboard")),
            ("Responsables", reverse("secretariat:guardians")),
            (str(self.guardian), None),
        ]
        return context

    def get_success_url(self):
        return reverse("secretariat:guardian-detail", args=[self.guardian.public_id])


class GuardianArchiveView(SecretariatViewMixin, View):
    academic_year_required = False

    def post(self, request, public_id):
        year = self.get_selected_academic_year()
        if year is not None and year.is_closed:
            messages.error(
                request,
                "Cette année scolaire est clôturée. Consultation uniquement.",
            )
            return redirect("secretariat:guardian-detail", public_id=public_id)
        guardian = get_object_or_404(Guardian, public_id=public_id)
        try:
            guardian_service.archive_guardian(guardian, actor=request.user, request=request)
            messages.success(request, "Responsable archivé.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:guardian-detail", public_id=public_id)


class GuardianRestoreView(SecretariatViewMixin, View):
    academic_year_required = False

    def post(self, request, public_id):
        year = self.get_selected_academic_year()
        if year is not None and year.is_closed:
            messages.error(
                request,
                "Cette année scolaire est clôturée. Consultation uniquement.",
            )
            return redirect("secretariat:guardian-detail", public_id=public_id)
        guardian = get_object_or_404(Guardian, public_id=public_id)
        try:
            guardian_service.restore_guardian(guardian, actor=request.user, request=request)
            messages.success(request, "Responsable restauré.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:guardian-detail", public_id=public_id)
