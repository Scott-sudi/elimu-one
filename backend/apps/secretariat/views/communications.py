"""Communication views."""

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView

from apps.secretariat.forms import CommunicationForm, CommunicationPublishForm
from apps.secretariat.forms.communication import students_in_class, _student_label
from apps.secretariat.models import Communication, CommunicationTarget, SchoolClass
from apps.secretariat.services import communication_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView, SecretariatViewMixin


class CommunicationClassStudentsView(SecretariatViewMixin, View):
    """JSON list of students enrolled in a class (for audience cascading selects)."""

    def get(self, request):
        year = self.get_selected_academic_year()
        class_id = request.GET.get("class_id", "").strip()
        if not class_id:
            return JsonResponse({"students": []})
        qs = SchoolClass.objects.filter(pk=class_id)
        if year:
            qs = qs.filter(academic_year=year)
        school_class = qs.first()
        if school_class is None:
            return JsonResponse({"students": []})
        students = [
            {"id": student.pk, "label": _student_label(student)}
            for student in students_in_class(school_class)
        ]
        return JsonResponse({"students": students})


def _format_target(target: CommunicationTarget) -> str:
    if target.target_type == CommunicationTarget.TargetType.ALL_PARENTS:
        return "Tous les parents (toutes les classes)"
    if target.target_type == CommunicationTarget.TargetType.CLASS and target.school_class:
        return f"Classe : {target.school_class.name}"
    if target.target_type == CommunicationTarget.TargetType.STUDENT and target.student:
        s = target.student
        name = " ".join(p for p in (s.nom, s.postnom, s.prenom) if p)
        return f"Élève : {s.matricule} — {name}"
    return target.get_target_type_display()


class CommunicationListView(SecretariatListView):
    template_name = "secretariat/communications/list.html"
    partial_template_name = "secretariat/communications/_table.html"
    context_object_name = "communications"
    page_title = "Communications"

    def get_queryset(self):
        year = self.get_selected_academic_year()
        from django.db.models import Exists, OuterRef

        qs = Communication.objects.select_related("author")
        if year:
            year_targeted = CommunicationTarget.objects.filter(
                communication_id=OuterRef("pk"),
                academic_year=year,
            )
            class_targeted = CommunicationTarget.objects.filter(
                communication_id=OuterRef("pk"),
                school_class__academic_year=year,
            )
            student_targeted = CommunicationTarget.objects.filter(
                communication_id=OuterRef("pk"),
                student__enrollments__academic_year=year,
            )
            all_parents = CommunicationTarget.objects.filter(
                communication_id=OuterRef("pk"),
                target_type=CommunicationTarget.TargetType.ALL_PARENTS,
            )
            has_any_target = CommunicationTarget.objects.filter(
                communication_id=OuterRef("pk"),
            )
            qs = qs.annotate(
                has_year_target=Exists(year_targeted),
                has_class_target=Exists(class_targeted),
                has_student_target=Exists(student_targeted),
                has_all_parents=Exists(all_parents),
                has_targets=Exists(has_any_target),
            ).filter(
                Q(has_year_target=True)
                | Q(has_class_target=True)
                | Q(has_student_target=True)
                | Q(has_all_parents=True)
                | Q(has_targets=False)
            )
        qs = qs.order_by("-is_pinned", "-published_at", "-created_at")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))
        filter_key = self.request.GET.get("filter") or self.request.GET.get("status", "")
        if filter_key == "pinned" or filter_key == "EPINGLEE":
            qs = qs.filter(is_pinned=True)
        elif filter_key:
            qs = qs.filter(status=filter_key)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_filter"] = (
            self.request.GET.get("filter") or self.request.GET.get("status", "")
        )
        context["year_writable"] = self.selected_year_is_writable()
        return context


class CommunicationCreateView(SecretariatViewMixin, FormView):
    form_class = CommunicationForm
    template_name = "secretariat/communications/create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["year"] = self.get_selected_academic_year()
        kwargs["include_status"] = False
        return kwargs

    def form_valid(self, form):
        try:
            self.require_writable_academic_year()
            data = form.cleaned_data.copy()
            data.pop("target_type", None)
            data.pop("school_class", None)
            data.pop("student", None)
            data.pop("status", None)
            communication = communication_service.create_draft(
                targets=[form.build_target()],
                actor=self.request.user,
                request=self.request,
                **data,
            )
            messages.success(self.request, "Brouillon créé.")
            return redirect(
                "secretariat:communication-detail", public_id=communication.public_id
            )
        except SecretariatError as exc:
            form.add_error(None, str(exc))
            messages.error(self.request, str(exc))
            return self.form_invalid(form)


class CommunicationUpdateView(SecretariatViewMixin, FormView):
    form_class = CommunicationForm
    template_name = "secretariat/communications/edit.html"

    def dispatch(self, request, *args, **kwargs):
        self.communication = get_object_or_404(Communication, public_id=kwargs["public_id"])
        year = self.get_selected_academic_year()
        if year and year.is_closed:
            messages.error(
                request,
                "Cette année scolaire est clôturée. Consultation uniquement — "
                "aucune modification n'est possible.",
            )
            return redirect(
                "secretariat:communication-detail",
                public_id=self.communication.public_id,
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.communication
        kwargs["year"] = self.get_selected_academic_year()
        kwargs["include_status"] = True
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["communication"] = self.communication
        context["breadcrumbs"] = [
            ("Secrétariat", reverse("secretariat:dashboard")),
            ("Communications", reverse("secretariat:communications")),
            (self.communication.title, reverse(
                "secretariat:communication-detail",
                kwargs={"public_id": self.communication.public_id},
            )),
            ("Modifier", None),
        ]
        return context

    def form_valid(self, form):
        try:
            self.require_writable_academic_year()
            data = form.cleaned_data.copy()
            data.pop("target_type", None)
            data.pop("school_class", None)
            data.pop("student", None)
            communication_service.update_communication(
                self.communication,
                targets=[form.build_target()],
                actor=self.request.user,
                request=self.request,
                **data,
            )
            messages.success(self.request, "Communication mise à jour.")
            return redirect(
                "secretariat:communication-detail",
                public_id=self.communication.public_id,
            )
        except SecretariatError as exc:
            form.add_error(None, str(exc))
            messages.error(self.request, str(exc))
            return self.form_invalid(form)


class CommunicationDetailView(SecretariatViewMixin, DetailView):
    model = Communication
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "communication"
    template_name = "secretariat/communications/detail.html"

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            "targets__school_class",
            "targets__student",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_academic_year()
        year_writable = bool(year and not year.is_closed)
        initial_target = self.object.targets.first()
        context["year_writable"] = year_writable
        context["target_labels"] = [_format_target(t) for t in self.object.targets.all()]
        context["publish_form"] = CommunicationPublishForm(
            year=year,
            initial_target=initial_target,
        )
        context["can_edit"] = (
            year_writable and self.object.status != Communication.Status.ARCHIVED
        )
        context["breadcrumbs"] = [
            ("Secrétariat", reverse("secretariat:dashboard")),
            ("Communications", reverse("secretariat:communications")),
            (self.object.title, None),
        ]
        return context


class CommunicationPublishView(SecretariatViewMixin, View):
    def post(self, request, public_id):
        communication = get_object_or_404(Communication, public_id=public_id)
        year = None
        try:
            year = self.require_writable_academic_year()
            form = CommunicationPublishForm(request.POST, year=year)
            if not form.is_valid():
                for errors in form.errors.values():
                    for error in errors:
                        messages.error(request, error)
                return redirect("secretariat:communication-detail", public_id=public_id)
            communication_service.publish(
                communication,
                targets=[form.build_target()],
                actor=request.user,
                request=request,
            )
            messages.success(request, "Communication publiée.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:communication-detail", public_id=public_id)


class CommunicationDeleteView(SecretariatViewMixin, View):
    def post(self, request, public_id):
        communication = get_object_or_404(Communication, public_id=public_id)
        try:
            self.require_writable_academic_year()
            communication_service.delete_communication(
                communication, actor=request.user, request=request
            )
            messages.success(request, "Communication supprimée.")
            return redirect("secretariat:communications")
        except SecretariatError as exc:
            messages.error(request, str(exc))
            return redirect("secretariat:communication-detail", public_id=public_id)


class _CommunicationActionMixin(SecretariatViewMixin, View):
    action = ""

    def _refresh_partial(self, request):
        list_view = CommunicationListView()
        list_view.request = request
        list_view.args = ()
        list_view.kwargs = {}
        list_view.object_list = list_view.get_queryset()
        context = list_view.get_context_data(object_list=list_view.object_list)
        from django.core.paginator import Paginator

        paginator = Paginator(list_view.object_list, list_view.paginate_by)
        page_obj = paginator.get_page(request.GET.get("page"))
        context["page_obj"] = page_obj
        html = render_to_string(
            "secretariat/communications/_table.html", context, request=request
        )
        return HttpResponse(html)

    def post(self, request, public_id):
        communication = get_object_or_404(Communication, public_id=public_id)
        try:
            self.require_writable_academic_year()
            if self.action == "pin":
                communication_service.pin(communication, actor=request.user, request=request)
                messages.success(request, "Communication épinglée.")
            elif self.action == "unpin":
                communication_service.unpin(communication, actor=request.user, request=request)
                messages.success(request, "Communication désépinglée.")
            elif self.action == "archive":
                communication_service.archive(communication, actor=request.user, request=request)
                messages.success(request, "Communication archivée.")
            elif self.action == "restore":
                communication_service.restore(communication, actor=request.user, request=request)
                messages.success(request, "Communication restaurée en brouillon.")
            else:
                messages.error(request, "Action invalide.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        if request.headers.get("HX-Request") == "true":
            return self._refresh_partial(request)
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url:
            return redirect(next_url)
        return redirect("secretariat:communication-detail", public_id=public_id)


class CommunicationPinView(_CommunicationActionMixin):
    action = "pin"


class CommunicationUnpinView(_CommunicationActionMixin):
    action = "unpin"


class CommunicationArchiveView(_CommunicationActionMixin):
    action = "archive"


class CommunicationRestoreView(_CommunicationActionMixin):
    action = "restore"
