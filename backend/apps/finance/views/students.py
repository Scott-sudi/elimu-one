"""Student finance situation and search for payments."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView

from apps.finance.services.situation_service import student_situation
from apps.secretariat.models import Enrollment, Student

from .base import FinanceViewMixin


class StudentSituationView(FinanceViewMixin, TemplateView):
    template_name = "finance/students/situation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        student = get_object_or_404(Student, public_id=kwargs["public_id"])
        situation = student_situation(student=student, academic_year=year)
        context.update(
            student=student,
            situation=situation,
            year_writable=not year.is_closed,
            breadcrumbs=[
                ("Comptabilité", reverse("finance:dashboard")),
                ("Situation élèves", reverse("finance:student-search")),
                (f"{student.nom} {student.prenom}".strip(), None),
            ],
        )
        return context


class StudentSearchView(FinanceViewMixin, TemplateView):
    """Search validated enrollments, then open student finance situation."""

    template_name = "finance/students/search.html"
    partial_template_name = "finance/students/_search_results.html"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return [self.partial_template_name]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.require_selected_year()
        q = self.request.GET.get("q", "").strip()
        enrollments = Enrollment.objects.none()
        if len(q) >= 2:
            enrollments = (
                Enrollment.objects.filter(
                    academic_year=year,
                    status=Enrollment.Status.VALIDATED,
                )
                .filter(
                    Q(student__matricule__icontains=q)
                    | Q(student__nom__icontains=q)
                    | Q(student__postnom__icontains=q)
                    | Q(student__prenom__icontains=q)
                    | Q(enrollment_number__icontains=q)
                )
                .select_related("student", "school_class")
                .order_by("student__nom", "student__postnom", "student__prenom")[:25]
            )
        context.update(
            enrollments=enrollments,
            q=q,
            breadcrumbs=[
                ("Comptabilité", reverse("finance:dashboard")),
                ("Situation élèves", None),
            ],
        )
        return context
