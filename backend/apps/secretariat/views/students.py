"""Student views."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.forms import StudentForm
from apps.secretariat.models import Student
from apps.secretariat.services import student_service
from apps.secretariat.services.document_service import document_completeness
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView, ServiceFormMixin


class StudentListView(SecretariatListView):
    template_name = "secretariat/students/list.html"
    partial_template_name = "secretariat/students/_table.html"
    context_object_name = "students"
    page_title = "Élèves"

    def get_queryset(self):
        qs = Student.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(matricule__icontains=q) | Q(nom__icontains=q) | Q(postnom__icontains=q) | Q(prenom__icontains=q))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(statut=status)
        return qs


class StudentCreateView(SecretaryRequiredMixin, ServiceFormMixin, FormView):
    form_class = StudentForm
    template_name = "secretariat/students/create.html"
    success_url_name = "secretariat:students"
    success_message = "Élève créé avec succès."

    def execute_service(self, form):
        return student_service.create_student(actor=self.request.user, request=self.request, **form.cleaned_data)


class StudentUpdateView(SecretaryRequiredMixin, ServiceFormMixin, FormView):
    form_class = StudentForm
    template_name = "secretariat/students/update.html"
    success_message = "Élève modifié."

    def dispatch(self, request, *args, **kwargs):
        self.student = get_object_or_404(Student, public_id=kwargs["public_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.student
        return kwargs

    def execute_service(self, form):
        return student_service.update_student(self.student, actor=self.request.user, request=self.request, **form.cleaned_data)

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


class StudentDetailView(SecretaryRequiredMixin, DetailView):
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
            breadcrumbs=[("Secrétariat", reverse("secretariat:dashboard")), ("Élèves", reverse("secretariat:students")), (self.object.matricule, None)],
        )
        return context


class StudentArchiveView(SecretaryRequiredMixin, View):
    def post(self, request, public_id):
        student = get_object_or_404(Student, public_id=public_id)
        try:
            student_service.archive_student(student, actor=request.user, request=request)
            messages.success(request, "Élève archivé.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:student-detail", public_id=public_id)
