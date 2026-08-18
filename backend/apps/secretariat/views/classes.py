"""School class views."""

from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView

from apps.secretariat.forms import SchoolClassForm, SchoolClassUpdateForm
from apps.secretariat.models import Enrollment, SchoolClass, StudentCard
from apps.secretariat.services import academic_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView, SecretariatViewMixin, ServiceFormMixin


class ClassListView(SecretariatListView):
    template_name = "secretariat/classes/list.html"
    partial_template_name = "secretariat/classes/_table.html"
    context_object_name = "classes"
    page_title = "Classes"
    paginate_by = 48

    def _year_classes(self):
        year = self.get_selected_academic_year()
        qs = SchoolClass.objects.select_related("academic_year", "level", "section", "option")
        if year:
            qs = qs.filter(academic_year=year)
        return qs

    def get_queryset(self):
        qs = self._year_classes().annotate(
            occupied=Count("enrollments", filter=Q(enrollments__status=Enrollment.Status.VALIDATED))
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))

        section_id = self.request.GET.get("section", "").strip()
        if section_id == "tronc":
            qs = qs.filter(section__isnull=True)
        elif section_id:
            qs = qs.filter(section__public_id=section_id)

        option_id = self.request.GET.get("option", "").strip()
        if option_id:
            qs = qs.filter(option__public_id=option_id)

        letter = self.request.GET.get("letter", "").strip().upper()
        allowed_letters = {choice for choice, _ in SchoolClass.LETTER_CHOICES}
        if letter in allowed_letters:
            qs = qs.filter(Q(letter=letter) | Q(letter="", code__iendswith=f"-{letter}"))

        level_id = self.request.GET.get("level", "").strip()
        if level_id:
            qs = qs.filter(level__public_id=level_id)

        return qs.order_by("level__order", "name")

    def get_context_data(self, **kwargs):
        from apps.secretariat.models import Option, SchoolLevel, Section

        context = super().get_context_data(**kwargs)
        context["form"] = SchoolClassForm()
        year = self.get_selected_academic_year()
        context["year_writable"] = bool(year and not year.is_closed)

        base = self._year_classes()
        context.update(
            filter_sections=Section.objects.filter(
                pk__in=base.exclude(section=None).values_list("section_id", flat=True)
            ).order_by("name"),
            filter_options=Option.objects.filter(
                pk__in=base.exclude(option=None).values_list("option_id", flat=True)
            ).select_related("section").order_by("name"),
            filter_levels=SchoolLevel.objects.filter(
                pk__in=base.values_list("level_id", flat=True)
            ).order_by("order", "name"),
            filter_letters=tuple(choice for choice, _ in SchoolClass.LETTER_CHOICES),
            has_tronc=base.filter(section__isnull=True).exists(),
            current_filters={
                "q": self.request.GET.get("q", ""),
                "section": self.request.GET.get("section", ""),
                "option": self.request.GET.get("option", ""),
                "letter": self.request.GET.get("letter", ""),
                "level": self.request.GET.get("level", ""),
            },
        )
        return context


class ClassCreateView(SecretariatViewMixin, ServiceFormMixin, FormView):
    form_class = SchoolClassForm
    template_name = "secretariat/classes/_form.html"
    success_url_name = "secretariat:classes"
    success_message = "Classe créée."

    def execute_service(self, form):
        year = self.require_writable_academic_year()
        return academic_service.create_school_class(
            actor=self.request.user,
            request=self.request,
            academic_year=year,
            **form.cleaned_data,
        )


class ClassUpdateView(SecretariatViewMixin, ServiceFormMixin, FormView):
    form_class = SchoolClassUpdateForm
    template_name = "secretariat/classes/update.html"
    success_message = "Classe modifiée."

    def dispatch(self, request, *args, **kwargs):
        self.school_class = get_object_or_404(SchoolClass, public_id=kwargs["public_id"])
        year = self.get_selected_academic_year()
        if year and year.is_closed:
            messages.error(
                request,
                "Cette année scolaire est clôturée. Consultation uniquement — "
                "aucune modification n'est possible.",
            )
            return redirect("secretariat:class-detail", public_id=self.school_class.public_id)
        if not self.school_class.is_active:
            messages.error(
                request,
                "Cette classe est désactivée. Consultation uniquement — aucune modification n'est possible.",
            )
            return redirect("secretariat:class-detail", public_id=self.school_class.public_id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.school_class
        return kwargs

    def execute_service(self, form):
        self.require_writable_academic_year()
        return academic_service.update_school_class(
            self.school_class,
            actor=self.request.user,
            request=self.request,
            **form.cleaned_data,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["school_class"] = self.school_class
        context["breadcrumbs"] = [
            ("Secrétariat", reverse("secretariat:dashboard")),
            ("Classes", reverse("secretariat:classes")),
            (self.school_class.name, None),
        ]
        return context

    def get_success_url(self):
        return reverse("secretariat:class-detail", args=[self.school_class.public_id])


class ClassActionView(SecretariatViewMixin, View):
    action = ""

    def post(self, request, public_id):
        school_class = get_object_or_404(SchoolClass, public_id=public_id)
        try:
            self.require_writable_academic_year()
            if self.action == "deactivate":
                academic_service.deactivate_school_class(
                    school_class, actor=request.user, request=request
                )
                messages.success(request, "Classe désactivée.")
            elif self.action == "reactivate":
                raise SecretariatError("La réactivation d'une classe n'est plus autorisée.")
            elif self.action == "delete":
                reason = request.POST.get("reason", "").strip()
                if not reason:
                    raise SecretariatError("Indiquez la raison de la suppression.")
                password = request.POST.get("password", "")
                if not password:
                    raise SecretariatError("Saisissez votre mot de passe pour confirmer la suppression.")
                if not request.user.check_password(password):
                    raise SecretariatError("Mot de passe incorrect. La suppression a été annulée.")
                academic_service.delete_school_class(
                    school_class,
                    deletion_reason=reason,
                    actor=request.user,
                    request=request,
                )
                messages.success(request, "Classe supprimée.")
                return redirect("secretariat:classes")
            elif self.action == "expand_capacity":
                password = request.POST.get("password", "")
                if not password:
                    raise SecretariatError(
                        "Saisissez votre mot de passe pour confirmer l'élargissement."
                    )
                if not request.user.check_password(password):
                    raise SecretariatError(
                        "Mot de passe incorrect. L'élargissement a été annulé."
                    )
                academic_service.expand_class_capacity(
                    school_class,
                    new_capacity=request.POST.get("new_capacity"),
                    reason=request.POST.get("reason", ""),
                    actor=request.user,
                    request=request,
                )
                messages.success(request, "Capacité de la classe élargie.")
                next_url = request.POST.get("next") or reverse(
                    "secretariat:class-detail", kwargs={"public_id": public_id}
                )
                return redirect(next_url)
            else:
                messages.error(request, "Action invalide.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        next_url = request.POST.get("next")
        if self.action == "expand_capacity" and next_url:
            return redirect(next_url)
        return redirect("secretariat:class-detail", public_id=public_id)


class ClassDetailView(SecretariatViewMixin, DetailView):
    model = SchoolClass
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "school_class"
    template_name = "secretariat/classes/detail.html"

    def get_queryset(self):
        year = self.get_selected_academic_year()
        qs = super().get_queryset().select_related("academic_year", "level", "section", "option")
        if year:
            qs = qs.filter(academic_year=year)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_students = self.object.enrollments.filter(status=Enrollment.Status.VALIDATED)
        occupied = all_students.count()
        girls = all_students.filter(student__sexe="F").count()
        boys = all_students.filter(student__sexe="M").count()

        students = (
            all_students.select_related("student")
            .prefetch_related(
                Prefetch(
                    "cards",
                    queryset=StudentCard.objects.order_by("-generated_at"),
                    to_attr="ordered_cards",
                )
            )
            .order_by("student__nom", "student__postnom", "student__prenom")
        )

        q = self.request.GET.get("q", "").strip()
        if q:
            students = students.filter(
                Q(student__matricule__icontains=q)
                | Q(student__nom__icontains=q)
                | Q(student__postnom__icontains=q)
                | Q(student__prenom__icontains=q)
                | Q(cards__card_number__icontains=q)
            ).distinct()

        sexe = self.request.GET.get("sexe", "").strip().upper()
        if sexe in {"M", "F"}:
            students = students.filter(student__sexe=sexe)

        enrollment_rows = []
        for enrollment in students:
            card = enrollment.ordered_cards[0] if enrollment.ordered_cards else None
            enrollment_rows.append({"enrollment": enrollment, "card": card})

        # Cartes générées (actives ou bloquées après clôture d'année)
        cards_ready_total = (
            StudentCard.objects.filter(
                enrollment__school_class=self.object,
                enrollment__status=Enrollment.Status.VALIDATED,
            )
            .values("enrollment_id")
            .distinct()
            .count()
        )

        context.update(
            enrollments=students,
            enrollment_rows=enrollment_rows,
            occupied=occupied,
            cards_ready=cards_ready_total,
            girls=girls,
            boys=boys,
            class_is_full=occupied >= self.object.max_capacity,
            class_writable=self.object.is_active and self.selected_year_is_writable(),
            year_writable=self.selected_year_is_writable(),
            student_filters={
                "q": q,
                "sexe": sexe,
            },
            breadcrumbs=[
                ("Secrétariat", reverse("secretariat:dashboard")),
                ("Classes", reverse("secretariat:classes")),
                (self.object.name, None),
            ],
        )
        return context
