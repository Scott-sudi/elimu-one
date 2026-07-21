"""Student document views."""

from pathlib import Path

from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from apps.core.mixins import SecretaryRequiredMixin
from apps.secretariat.forms import StudentDocumentForm
from apps.secretariat.models import StudentDocument
from apps.secretariat.services import document_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView


class DocumentListView(SecretariatListView):
    template_name = "secretariat/documents/list.html"
    partial_template_name = "secretariat/documents/_table.html"
    context_object_name = "documents"
    page_title = "Documents"

    def get_queryset(self):
        qs = StudentDocument.objects.select_related("student", "document_type", "verified_by")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(student__matricule__icontains=q) | Q(student__nom__icontains=q) | Q(document_type__name__icontains=q))
        if self.request.GET.get("status"):
            qs = qs.filter(verification_status=self.request.GET["status"])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = StudentDocumentForm()
        return context

    def post(self, request, *args, **kwargs):
        form = StudentDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data.copy()
            try:
                document_service.upload_document(actor=request.user, request=request, **data)
                messages.success(request, "Document ajouté.")
            except SecretariatError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Veuillez corriger le formulaire.")
        return redirect("secretariat:documents")


class DocumentVerifyView(SecretaryRequiredMixin, View):
    def post(self, request, public_id):
        document = get_object_or_404(StudentDocument, public_id=public_id)
        try:
            document_service.verify_document(
                document, status=request.POST.get("status", ""),
                observation=request.POST.get("observation", ""),
                actor=request.user, request=request,
            )
            messages.success(request, "Statut du document mis à jour.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:documents")


class DocumentDownloadView(SecretaryRequiredMixin, View):
    """Stream a student document only after role authorization."""

    def get(self, request, public_id):
        document = get_object_or_404(StudentDocument, public_id=public_id)
        document.file.open("rb")
        return FileResponse(
            document.file,
            as_attachment=True,
            filename=Path(document.file.name).name,
        )
