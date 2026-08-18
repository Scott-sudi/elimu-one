"""Student views."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView

from apps.secretariat.forms import StudentForm
from apps.secretariat.models import Enrollment, Student
from apps.secretariat.services import student_service
from apps.secretariat.services.document_service import document_completeness
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView, SecretariatViewMixin, ServiceFormMixin


class StudentListView(SecretariatListView):
    template_name = "secretariat/students/list.html"
    partial_template_name = "secretariat/students/_table.html"
    context_object_name = "students"
    page_title = "Élèves"

    def get_queryset(self):
        qs = Student.objects.all()
        year = self.get_selected_academic_year()
        scope = self.request.GET.get("scope", "").strip()
        # Primary: students with a validated enrollment in the selected year.
        # ?scope=all allows searching unenrolled / other-year students.
        if scope != "all" and year:
            qs = qs.filter(
                enrollments__academic_year=year,
                enrollments__status=Enrollment.Status.VALIDATED,
            ).distinct()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(matricule__icontains=q)
                | Q(nom__icontains=q)
                | Q(postnom__icontains=q)
                | Q(prenom__icontains=q)
            )
        status = self.request.GET.get("status")
        if status == "ARCHIVE" or status == Student.Status.ARCHIVED:
            qs = qs.filter(is_archived=True)
        elif status:
            qs = qs.filter(statut=status, is_archived=False)
        elif scope != "all":
            # Default list hides archived unless explicitly filtered.
            qs = qs.filter(is_archived=False)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["scope"] = self.request.GET.get("scope", "")
        return context


class StudentCreateView(SecretariatViewMixin, ServiceFormMixin, FormView):
    form_class = StudentForm
    template_name = "secretariat/students/create.html"
    success_url_name = "secretariat:students"
    success_message = "Élève créé avec succès."

    def execute_service(self, form):
        self.require_writable_academic_year()
        return student_service.create_student(
            actor=self.request.user, request=self.request, **form.cleaned_data
        )


class StudentUpdateView(SecretariatViewMixin, ServiceFormMixin, FormView):
    form_class = StudentForm
    template_name = "secretariat/students/update.html"
    success_message = "Élève modifié."

    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student, public_id=kwargs["public_id"])
        year = self.get_selected_academic_year()
        if year and year.is_closed:
            messages.error(
                request,
                "Cette année scolaire est clôturée. Consultation uniquement — "
                "aucune modification n'est possible.",
            )
            return redirect("secretariat:student-detail", public_id=self.student.public_id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.student
        return kwargs

    def execute_service(self, form):
        self.require_writable_academic_year()
        return student_service.update_student(
            self.student, actor=self.request.user, request=self.request, **form.cleaned_data
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["student"] = self.student
        context["breadcrumbs"] = [
            ("Secrétariat", reverse("secretariat:dashboard")),
            ("Élèves", reverse("secretariat:students")),
            (self.student.matricule, None),
        ]
        return context

    def get_success_url(self):
        return reverse("secretariat:student-detail", args=[self.student.public_id])


class StudentDetailView(SecretariatViewMixin, DetailView):
    model = Student
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "student"
    template_name = "secretariat/students/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            guardian_links=self.object.guardian_links.select_related("guardian"),
            enrollments=self.object.enrollments.select_related("academic_year", "school_class"),
            documents=self.object.documents.select_related("document_type"),
            cards=self.object.cards.select_related("enrollment"),
            document_status=document_completeness(self.object),
            year_writable=self.selected_year_is_writable(),
            breadcrumbs=[
                ("Secrétariat", reverse("secretariat:dashboard")),
                ("Classes", reverse("secretariat:classes")),
                (self.object.matricule, None),
            ],
        )
        return context


class StudentArchiveView(SecretariatViewMixin, View):
    def post(self, request, public_id):
        student = get_object_or_404(Student, public_id=public_id)
        try:
            self.require_writable_academic_year()
            student_service.archive_student(student, actor=request.user, request=request)
            messages.success(request, "Élève archivé.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:student-detail", public_id=public_id)


class StudentDeleteView(SecretariatViewMixin, View):
    """Delete (archive) a student from a class, with password + motif."""

    def post(self, request, public_id):
        student = get_object_or_404(Student, public_id=public_id)
        next_url = request.POST.get("next") or reverse(
            "secretariat:student-detail", kwargs={"public_id": public_id}
        )
        try:
            self.require_writable_academic_year()
            reason = (request.POST.get("reason") or "").strip()
            if not reason:
                raise SecretariatError("Indiquez le motif de la suppression.")
            password = request.POST.get("password", "")
            if not password:
                raise SecretariatError(
                    "Saisissez votre mot de passe secrétaire pour confirmer."
                )
            if not request.user.check_password(password):
                raise SecretariatError(
                    "Mot de passe incorrect. La suppression a été annulée."
                )
            student_service.delete_student_from_school(
                student,
                reason=reason,
                actor=request.user,
                request=request,
            )
            messages.success(
                request,
                f"Élève {student.matricule} supprimé. "
                "Il n’apparaît plus dans la classe ni dans l’application parents.",
            )
        except SecretariatError as exc:
            messages.error(request, str(exc))
            return redirect(next_url)
        return redirect(next_url)


class StudentRestoreView(SecretariatViewMixin, View):
    def post(self, request, public_id):
        student = get_object_or_404(Student, public_id=public_id)
        try:
            self.require_writable_academic_year()
            student_service.restore_student(student, actor=request.user, request=request)
            messages.success(request, "Élève restauré.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:student-detail", public_id=public_id)
