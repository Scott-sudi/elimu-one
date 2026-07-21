"""Document forms."""

from apps.secretariat.models import DocumentType, StudentDocument

from .academic import StyledModelForm


class DocumentTypeForm(StyledModelForm):
    class Meta:
        model = DocumentType
        fields = ("name", "code", "is_required", "level", "description", "is_active")
        labels = {
            "name": "Nom", "code": "Code", "is_required": "Obligatoire",
            "level": "Niveau", "description": "Description", "is_active": "Actif",
        }


class StudentDocumentForm(StyledModelForm):
    class Meta:
        model = StudentDocument
        fields = ("student", "document_type", "file", "observation")
        labels = {
            "student": "Élève", "document_type": "Type de document",
            "file": "Fichier", "observation": "Observation",
        }
