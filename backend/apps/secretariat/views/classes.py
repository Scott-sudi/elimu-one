"""School class views."""

from django.db.models import Count, Q
from django.urls import reverse
from django.views.generic import DetailView, FormView

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.forms import SchoolClassForm
from apps.secretariat.models import Enrollment, SchoolClass
from apps.secretariat.services import academic_service

from .base import SecretariatListView, ServiceFormMixin


class ClassListView(SecretariatListView):
    template_name = "secretariat/classes/list.html"
    partial_template_name = "secretariat/classes/_table.html"
    context_object_name = "classes"
    page_title = "Classes"

    def get_queryset(self):
        qs = SchoolClass.objects.select_related("academic_year", "level", "section", "option").annotate(
            occupied=Count("enrollments", filter=Q(enrollments__status=Enrollment.Status.VALIDATED))
        )
        if self.request.GET.get("year"):
            qs = qs.filter(academic_year__public_id=self.request.GET["year"])
        if self.request.GET.get("q"):
            qs = qs.filter(Q(name__icontains=self.request.GET["q"]) | Q(code__icontains=self.request.GET["q"]))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = SchoolClassForm()
        return context


class ClassCreateView(SecretaryRequiredMixin, ServiceFormMixin, FormView):
    form_class = SchoolClassForm
    template_name = "secretariat/classes/_form.html"
    success_url_name = "secretariat:classes"
    success_message = "Classe créée."

    def execute_service(self, form):
        return academic_service.create_school_class(actor=self.request.user, request=self.request, **form.cleaned_data)


class ClassDetailView(SecretaryRequiredMixin, DetailView):
    model = SchoolClass
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "school_class"
    template_name = "secretariat/classes/detail.html"

    def get_queryset(self):
        return super().get_queryset().select_related("academic_year", "level", "section", "option")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        students = self.object.enrollments.filter(status=Enrollment.Status.VALIDATED).select_related("student")
        context.update(
            enrollments=students,
            occupied=students.count(),
            girls=students.filter(student__sexe="F").count(),
            boys=students.filter(student__sexe="M").count(),
            breadcrumbs=[("Secrétariat", reverse("secretariat:dashboard")), ("Classes", reverse("secretariat:classes")), (self.object.name, None)],
        )
        return context
