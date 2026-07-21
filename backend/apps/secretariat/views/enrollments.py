"""Enrollment, reenrollment, and transfer views."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.forms import EnrollmentForm, ReenrollmentForm, TransferForm
from apps.secretariat.models import ClassTransfer, Enrollment, SchoolClass
from apps.secretariat.services import enrollment_service, reenrollment_service, transfer_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView, ServiceFormMixin


class EnrollmentListView(SecretariatListView):
    template_name = "secretariat/enrollments/list.html"
    partial_template_name = "secretariat/enrollments/_table.html"
    context_object_name = "enrollments"
    page_title = "Inscriptions"

    def get_queryset(self):
        qs = Enrollment.objects.select_related("student", "academic_year", "school_class")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(enrollment_number__icontains=q) | Q(student__matricule__icontains=q) | Q(student__nom__icontains=q))
        if self.request.GET.get("status"):
            qs = qs.filter(status=self.request.GET["status"])
        return qs


class EnrollmentCreateView(SecretaryRequiredMixin, ServiceFormMixin, FormView):
    form_class = EnrollmentForm
    template_name = "secretariat/enrollments/create.html"
    success_url_name = "secretariat:enrollments"
    success_message = "Inscription enregistrée."

    def execute_service(self, form):
        data = form.cleaned_data.copy()
        student = data.pop("student")
        school_class = data.pop("school_class")
        return enrollment_service.create_enrollment(
            student=student, school_class=school_class,
            actor=self.request.user, request=self.request, **data,
        )


class ReenrollmentView(SecretaryRequiredMixin, FormView):
    form_class = ReenrollmentForm
    template_name = "secretariat/enrollments/reenroll.html"

    def form_valid(self, form):
        try:
            reenrollment_service.reenroll_student(
                previous_enrollment=form.cleaned_data["previous_enrollment"],
                target_class=form.cleaned_data["target_class"],
                force_over_capacity=form.cleaned_data["force_over_capacity"],
                actor=self.request.user, request=self.request,
            )
            messages.success(self.request, "Réinscription effectuée.")
            return redirect("secretariat:reenrollments")
        except SecretariatError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recent_reenrollments"] = Enrollment.objects.filter(
            enrollment_type=Enrollment.EnrollmentType.RENEWAL
        ).select_related("student", "school_class")[:20]
        context["reenrollment_candidates"] = Enrollment.objects.filter(
            status__in=(Enrollment.Status.VALIDATED, Enrollment.Status.CLOSED)
        ).select_related("student", "school_class", "academic_year")[:100]
        context["target_classes"] = SchoolClass.objects.filter(
            is_active=True, academic_year__is_closed=False
        ).select_related("academic_year")
        return context


class BulkReenrollmentView(SecretaryRequiredMixin, FormView):
    form_class = ReenrollmentForm
    template_name = "secretariat/enrollments/reenroll.html"

    def post(self, request, *args, **kwargs):
        try:
            target_class = SchoolClass.objects.filter(public_id=request.POST.get("target_class")).first()
            enrollments = list(
                Enrollment.objects.filter(public_id__in=request.POST.getlist("enrollments"))
            )
        except (ValidationError, ValueError):
            target_class, enrollments = None, []
        if not target_class or not enrollments:
            messages.error(request, "Sélectionnez des inscriptions et une classe de destination.")
            return redirect("secretariat:reenrollments")
        try:
            reenrollment_service.bulk_reenroll(
                [(enrollment, target_class) for enrollment in enrollments],
                force_over_capacity=bool(request.POST.get("force_over_capacity")),
                actor=request.user, request=request,
            )
            messages.success(request, f"{len(enrollments)} élève(s) réinscrit(s).")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:reenrollments")


class TransferView(SecretaryRequiredMixin, FormView):
    form_class = TransferForm
    template_name = "secretariat/enrollments/transfer.html"

    def form_valid(self, form):
        try:
            transfer_service.transfer_student(
                actor=self.request.user, request=self.request, **form.cleaned_data
            )
            messages.success(self.request, "Transfert effectué.")
            return redirect("secretariat:transfers")
        except SecretariatError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["transfers"] = ClassTransfer.objects.select_related("student", "from_class", "to_class")[:25]
        context["breadcrumbs"] = [("Secrétariat", reverse("secretariat:dashboard")), ("Transferts", None)]
        return context
