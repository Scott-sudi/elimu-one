"""Student document views."""

from pathlib import Path

from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from apps.secretariat.forms import StudentDocumentForm
from apps.secretariat.models import Enrollment, StudentDocument
from apps.secretariat.services import document_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView, SecretariatViewMixin


class DocumentListView(SecretariatListView):
    template_name = "secretariat/documents/list.html"
    partial_template_name = "secretariat/documents/_table.html"
    context_object_name = "documents"
    page_title = "Documents"

    def get_queryset(self):
        year = self.get_selected_academic_year()
        qs = StudentDocument.objects.select_related("student", "document_type", "verified_by")
        # Scope to students enrolled in the selected year (primary).
        if year:
            qs = qs.filter(
                student__enrollments__academic_year=year,
                student__enrollments__status=Enrollment.Status.VALIDATED,
            ).distinct()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(student__matricule__icontains=q)
                | Q(student__nom__icontains=q)
                | Q(document_type__name__icontains=q)
            )
        if self.request.GET.get("status"):
            qs = qs.filter(verification_status=self.request.GET["status"])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = StudentDocumentForm()
        context["year_writable"] = self.selected_year_is_writable()
        return context

    def post(self, request, *args, **kwargs):
        try:
            self.require_writable_academic_year()
        except SecretariatError as exc:
            messages.error(request, str(exc))
            return redirect("secretariat:documents")
        form = StudentDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data.copy()
            try:
                document_service.upload_document(
                    actor=request.user, request=request, **data
                )
                messages.success(request, "Document ajouté.")
            except SecretariatError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Veuillez corriger le formulaire.")
        return redirect("secretariat:documents")


class DocumentVerifyView(SecretariatViewMixin, View):
    def post(self, request, public_id):
        try:
            self.require_writable_academic_year()
        except SecretariatError as exc:
            messages.error(request, str(exc))
            return redirect("secretariat:documents")
        document = get_object_or_404(StudentDocument, public_id=public_id)
        try:
            document_service.verify_document(
                document,
                status=request.POST.get("status", ""),
                observation=request.POST.get("observation", ""),
                actor=request.user,
                request=request,
            )
            messages.success(request, "Statut du document mis à jour.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:documents")


class DocumentDownloadView(SecretariatViewMixin, View):
    """Stream a student document only after role authorization."""

    def get(self, request, public_id):
        document = get_object_or_404(StudentDocument, public_id=public_id)
        document.file.open("rb")
        return FileResponse(
            document.file,
            as_attachment=True,
            filename=Path(document.file.name).name,
        )
