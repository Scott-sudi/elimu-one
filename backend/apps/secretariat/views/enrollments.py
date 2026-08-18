"""Enrollment, reenrollment, and transfer views."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from apps.secretariat.forms import EnrollmentForm, ReenrollmentForm, TransferForm
from apps.secretariat.models import ClassTransfer, Enrollment, SchoolClass
from apps.secretariat.services import enrollment_service, reenrollment_service, transfer_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView, SecretariatViewMixin, ServiceFormMixin


class EnrollmentListView(SecretariatListView):
    template_name = "secretariat/enrollments/list.html"
    partial_template_name = "secretariat/enrollments/_table.html"
    context_object_name = "enrollments"
    page_title = "Inscriptions"

    def get_queryset(self):
        year = self.get_selected_academic_year()
        qs = Enrollment.objects.select_related("student", "academic_year", "school_class")
        if year:
            qs = qs.filter(academic_year=year)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(enrollment_number__icontains=q)
                | Q(student__matricule__icontains=q)
                | Q(student__nom__icontains=q)
            )
        if self.request.GET.get("status"):
            qs = qs.filter(status=self.request.GET["status"])
        return qs


class EnrollmentCreateView(SecretariatViewMixin, ServiceFormMixin, FormView):
    form_class = EnrollmentForm
    template_name = "secretariat/enrollments/create.html"
    success_url_name = "secretariat:enrollments"
    success_message = "Inscription enregistrée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        year = self.get_selected_academic_year()
        if year:
            form.fields["school_class"].queryset = SchoolClass.objects.filter(
                academic_year=year, is_active=True
            )
        return form

    def execute_service(self, form):
        year = self.require_writable_academic_year()
        data = form.cleaned_data.copy()
        student = data.pop("student")
        school_class = data.pop("school_class")
        if school_class.academic_year_id != year.pk:
            raise SecretariatError(
                "La classe sélectionnée n'appartient pas à l'année scolaire en cours."
            )
        return enrollment_service.create_enrollment(
            student=student,
            school_class=school_class,
            actor=self.request.user,
            request=self.request,
            **data,
        )


class ReenrollmentView(SecretariatViewMixin, FormView):
    form_class = ReenrollmentForm
    template_name = "secretariat/enrollments/reenroll.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        year = self.get_selected_academic_year()
        if year:
            form.fields["target_class"].queryset = SchoolClass.objects.filter(
                academic_year=year, is_active=True
            )
        return form

    def form_valid(self, form):
        try:
            year = self.require_writable_academic_year()
            target_class = form.cleaned_data["target_class"]
            if target_class.academic_year_id != year.pk:
                raise SecretariatError(
                    "La classe de destination doit appartenir à l'année scolaire sélectionnée."
                )
            reenrollment_service.reenroll_student(
                previous_enrollment=form.cleaned_data["previous_enrollment"],
                target_class=target_class,
                force_over_capacity=form.cleaned_data["force_over_capacity"],
                actor=self.request.user,
                request=self.request,
            )
            messages.success(self.request, "Réinscription effectuée.")
            return redirect("secretariat:reenrollments")
        except SecretariatError as exc:
            form.add_error(None, str(exc))
            messages.error(self.request, str(exc))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_academic_year()
        context["recent_reenrollments"] = Enrollment.objects.filter(
            enrollment_type=Enrollment.EnrollmentType.RENEWAL,
            academic_year=year,
        ).select_related("student", "school_class")[:20]
        # Prefer class-scoped flow; keep a generic candidate list narrowed by previous closed year.
        previous = reenrollment_service.get_previous_closed_year(year) if year else None
        candidates = Enrollment.objects.none()
        if previous:
            already = Enrollment.objects.filter(
                academic_year=year,
                status__in=(Enrollment.Status.DRAFT, Enrollment.Status.VALIDATED),
            ).values_list("student_id", flat=True)
            candidates = (
                Enrollment.objects.filter(
                    academic_year=previous,
                    status__in=(Enrollment.Status.VALIDATED, Enrollment.Status.CLOSED),
                )
                .exclude(student_id__in=already)
                .select_related("student", "school_class", "academic_year")
                .order_by("student__nom")[:200]
            )
        context["reenrollment_candidates"] = candidates
        context["target_classes"] = SchoolClass.objects.filter(
            is_active=True, academic_year=year
        ).select_related("academic_year")
        context["year_writable"] = bool(year and not year.is_closed)
        context["breadcrumbs"] = [
            ("Secrétariat", reverse("secretariat:dashboard")),
            ("Réinscriptions", None),
        ]
        return context


class BulkReenrollmentView(SecretariatViewMixin, FormView):
    form_class = ReenrollmentForm
    template_name = "secretariat/enrollments/reenroll.html"

    def post(self, request, *args, **kwargs):
        try:
            year = self.require_writable_academic_year()
            target_class = SchoolClass.objects.filter(
                public_id=request.POST.get("target_class"),
                academic_year=year,
            ).first()
            enrollments = list(
                Enrollment.objects.filter(public_id__in=request.POST.getlist("enrollments"))
            )
        except (ValidationError, ValueError, SecretariatError) as exc:
            if isinstance(exc, SecretariatError):
                messages.error(request, str(exc))
            else:
                messages.error(request, "Sélectionnez des inscriptions et une classe de destination.")
            return redirect("secretariat:reenrollments")
        if not target_class or not enrollments:
            messages.error(request, "Sélectionnez des inscriptions et une classe de destination.")
            return redirect("secretariat:reenrollments")
        try:
            reenrollment_service.bulk_reenroll(
                [(enrollment, target_class) for enrollment in enrollments],
                force_over_capacity=bool(request.POST.get("force_over_capacity")),
                actor=request.user,
                request=request,
            )
            messages.success(request, f"{len(enrollments)} élève(s) réinscrit(s).")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:reenrollments")


class TransferView(SecretariatViewMixin, FormView):
    form_class = TransferForm
    template_name = "secretariat/enrollments/transfer.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        year = self.get_selected_academic_year()
        if year:
            form.fields["enrollment"].queryset = Enrollment.objects.filter(
                status=Enrollment.Status.VALIDATED,
                academic_year=year,
            )
            form.fields["to_class"].queryset = SchoolClass.objects.filter(
                academic_year=year, is_active=True
            )
        return form

    def form_valid(self, form):
        try:
            year = self.require_writable_academic_year()
            enrollment = form.cleaned_data["enrollment"]
            to_class = form.cleaned_data["to_class"]
            if enrollment.academic_year_id != year.pk or to_class.academic_year_id != year.pk:
                raise SecretariatError(
                    "Le transfert doit concerner l'année scolaire sélectionnée."
                )
            transfer_service.transfer_student(
                actor=self.request.user, request=self.request, **form.cleaned_data
            )
            messages.success(self.request, "Transfert effectué.")
            return redirect("secretariat:transfers")
        except SecretariatError as exc:
            form.add_error(None, str(exc))
            messages.error(self.request, str(exc))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_academic_year()
        transfers = ClassTransfer.objects.select_related(
            "student", "from_class", "to_class", "enrollment"
        )
        if year:
            transfers = transfers.filter(
                Q(enrollment__academic_year=year)
                | Q(from_class__academic_year=year)
                | Q(to_class__academic_year=year)
            )
        context["transfers"] = transfers[:25]
        context["year_writable"] = bool(year and not year.is_closed)
        context["breadcrumbs"] = [("Secrétariat", reverse("secretariat:dashboard")), ("Transferts", None)]
        return context
