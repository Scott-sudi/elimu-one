"""Class-scoped inscription and réinscription views."""

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView

from apps.secretariat.forms import ClassNewStudentForm, ClassReenrollmentForm
from apps.secretariat.models import Enrollment, SchoolClass
from apps.secretariat.services import (
    enrollment_service,
    guardian_service,
    reenrollment_service,
    student_service,
)
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatViewMixin


def _class_occupancy(school_class: SchoolClass) -> tuple[int, bool]:
    occupied = Enrollment.objects.filter(
        school_class=school_class,
        status=Enrollment.Status.VALIDATED,
    ).count()
    return occupied, occupied >= school_class.max_capacity


class ClassEnrollmentMixin(SecretariatViewMixin):
    """Resolve the target class for class-scoped enrollment flows."""

    school_class: SchoolClass

    def dispatch(self, request, *args, **kwargs):
        year = self.get_selected_academic_year()
        qs = SchoolClass.objects.select_related("academic_year", "level", "section", "option")
        if year:
            qs = qs.filter(academic_year=year)
        self.school_class = get_object_or_404(qs, public_id=kwargs["public_id"])
        if not self.school_class.is_active:
            messages.error(
                request,
                "Cette classe est désactivée. Consultation uniquement — aucune modification n'est possible.",
            )
            return redirect("secretariat:class-detail", public_id=self.school_class.public_id)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("secretariat:class-detail", kwargs={"public_id": self.school_class.public_id})

    def class_breadcrumbs(self, current_label: str):
        return [
            ("Secrétariat", reverse("secretariat:dashboard")),
            ("Classes", reverse("secretariat:classes")),
            (self.school_class.name, reverse("secretariat:class-detail", kwargs={"public_id": self.school_class.public_id})),
            (current_label, None),
        ]

    def occupancy_context(self) -> dict:
        occupied, class_is_full = _class_occupancy(self.school_class)
        return {
            "occupied": occupied,
            "class_is_full": class_is_full,
        }


class ClassInscriptionView(ClassEnrollmentMixin, FormView):
    """Inscription d'un nouvel élève dans une classe."""

    form_class = ClassNewStudentForm
    template_name = "secretariat/classes/enroll.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            school_class=self.school_class,
            year_writable=self.selected_year_is_writable(),
            breadcrumbs=self.class_breadcrumbs("Inscription"),
            guardian_lookup_url=reverse("secretariat:guardian-phone-lookup"),
            **self.occupancy_context(),
        )
        return context

    def form_valid(self, form):
        try:
            year = self.require_writable_academic_year()
            if self.school_class.academic_year_id != year.pk:
                raise SecretariatError("Cette classe n'appartient pas à l'année scolaire sélectionnée.")
            data = form.cleaned_data.copy()
            provenance = data.pop("provenance", "")
            observation = data.pop("observation", "")
            data.pop("telephone_responsable", None)
            guardian = form.get_guardian()
            if guardian is None:
                raise SecretariatError(
                    "Aucun responsable n'est enregistré avec ce numéro de téléphone. "
                    "Créez d'abord le responsable dans le menu Responsables."
                )
            with transaction.atomic():
                student = student_service.create_student(
                    school_class=self.school_class,
                    actor=self.request.user,
                    request=self.request,
                    **data,
                )
                enrollment_service.create_enrollment(
                    student=student,
                    school_class=self.school_class,
                    enrollment_type=Enrollment.EnrollmentType.NEW,
                    force_over_capacity=False,
                    provenance=provenance,
                    observation=observation,
                    actor=self.request.user,
                    request=self.request,
                )
                guardian_service.associate_guardian(
                    student=student,
                    guardian=guardian,
                    lien_parente=guardian_service.default_relationship_for_guardian(guardian),
                    is_primary=True,
                    actor=self.request.user,
                    request=self.request,
                )
            messages.success(
                self.request,
                f"Inscription enregistrée : {student.matricule} dans {self.school_class.name}.",
            )
            return redirect(self.get_success_url())
        except SecretariatError as exc:
            form.add_error(None, str(exc))
            messages.error(self.request, str(exc))
            return self.form_invalid(form)


class ClassReenrollmentView(ClassEnrollmentMixin, FormView):
    """Réinscription into a fixed class from the previous closed year."""

    form_class = ClassReenrollmentForm
    template_name = "secretariat/classes/reenroll.html"

    def get_candidates(self):
        return reenrollment_service.eligible_reenrollments_for_class(self.school_class)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["queryset"] = self.get_candidates()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        previous_year = reenrollment_service.get_previous_closed_year(self.school_class.academic_year)
        source_order = reenrollment_service.source_level_order_for(self.school_class)
        candidates = self.get_candidates()
        context.update(
            school_class=self.school_class,
            previous_year=previous_year,
            source_order=source_order,
            candidates=candidates,
            candidates_count=candidates.count(),
            year_writable=self.selected_year_is_writable(),
            breadcrumbs=self.class_breadcrumbs("Réinscription"),
            **self.occupancy_context(),
        )
        return context

    def form_valid(self, form):
        try:
            year = self.require_writable_academic_year()
            if self.school_class.academic_year_id != year.pk:
                raise SecretariatError("Cette classe n'appartient pas à l'année scolaire sélectionnée.")
            previous = form.cleaned_data["previous_enrollment"]
            with transaction.atomic():
                reenrollment_service.reenroll_student(
                    previous_enrollment=previous,
                    target_class=self.school_class,
                    force_over_capacity=False,
                    actor=self.request.user,
                    request=self.request,
                )
            messages.success(self.request, "Réinscription effectuée.")
            return redirect(self.get_success_url())
        except SecretariatError as exc:
            form.add_error(None, str(exc))
            messages.error(self.request, str(exc))
            return self.form_invalid(form)


class ClassBulkReenrollmentView(ClassEnrollmentMixin, View):
    """Bulk réinscription of selected previous-year enrollments into this class."""

    def post(self, request, *args, **kwargs):
        try:
            year = self.require_writable_academic_year()
            if self.school_class.academic_year_id != year.pk:
                raise SecretariatError("Cette classe n'appartient pas à l'année scolaire sélectionnée.")
            enrollments = list(
                reenrollment_service.eligible_reenrollments_for_class(self.school_class).filter(
                    public_id__in=request.POST.getlist("enrollments")
                )
            )
            if not enrollments:
                raise SecretariatError("Sélectionnez au moins un élève éligible.")
            reenrollment_service.bulk_reenroll(
                [(enrollment, self.school_class) for enrollment in enrollments],
                force_over_capacity=False,
                actor=request.user,
                request=request,
            )
            messages.success(request, f"{len(enrollments)} élève(s) réinscrit(s).")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:class-reenroll", public_id=self.school_class.public_id)


class GuardianPhoneLookupView(SecretariatViewMixin, View):
    """JSON typeahead: phone digits → matching responsables (or new number)."""

    def get(self, request, *args, **kwargs):
        from apps.secretariat.services.guardian_identification_service import (
            next_guardian_identification,
            suggest_guardian_identification_for_class,
        )

        phone = (request.GET.get("phone") or "").strip()
        class_public_id = (request.GET.get("class_id") or "").strip()
        school_class = None
        if class_public_id:
            school_class = (
                SchoolClass.objects.select_related("academic_year", "section", "option")
                .filter(public_id=class_public_id)
                .first()
            )

        suggested = ""
        if school_class is not None:
            suggested = suggest_guardian_identification_for_class(school_class=school_class)
        else:
            year = self.get_selected_academic_year()
            year_start = year.start_date.year if year and year.start_date else None
            if year_start:
                suggested = next_guardian_identification(academic_year_start=year_start)

        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) < 3:
            return JsonResponse(
                {
                    "found": False,
                    "matches": [],
                    "suggested_numero_identification": suggested,
                }
            )

        def serialize(guardian):
            full_name = " ".join(
                part for part in (guardian.nom, guardian.postnom, guardian.prenom) if part
            )
            return {
                "numero_identification": guardian.numero_identification or "",
                "nom": guardian.nom,
                "postnom": guardian.postnom or "",
                "prenom": guardian.prenom,
                "full_name": full_name,
                "telephone_principal": guardian.telephone_principal or "",
                "telephone_secondaire": guardian.telephone_secondaire or "",
            }

        exact = guardian_service.find_guardian_by_phone(phone)
        matches = guardian_service.search_guardians_by_phone_digits(phone, limit=8)
        payload_matches = [serialize(g) for g in matches]

        if exact is not None:
            data = serialize(exact)
            data["found"] = True
            data["matches"] = payload_matches
            data["suggested_numero_identification"] = suggested
            return JsonResponse(data)

        return JsonResponse(
            {
                "found": False,
                "matches": payload_matches,
                "suggested_numero_identification": suggested,
            }
        )
