"""Student forms."""

from django import forms

from apps.secretariat.models import Student

from .academic import StyledModelForm


class StudentForm(StyledModelForm):
    class Meta:
        model = Student
        exclude = ("matricule", "is_archived", "created_at", "updated_at", "public_id")
        labels = {
            "nom": "Nom", "postnom": "Postnom", "prenom": "Prénom", "sexe": "Sexe",
            "date_naissance": "Date de naissance", "lieu_naissance": "Lieu de naissance",
            "nationalite": "Nationalité", "adresse": "Adresse", "photo": "Photo",
            "ancien_etablissement": "Ancien établissement", "date_admission": "Date d'admission",
            "statut": "Statut", "groupe_sanguin": "Groupe sanguin", "allergies": "Allergies",
            "conditions_medicales": "Conditions médicales", "observations": "Observations",
        }
        widgets = {
            "date_naissance": forms.DateInput(attrs={"type": "date"}),
            "date_admission": forms.DateInput(attrs={"type": "date"}),
            "adresse": forms.Textarea(attrs={"rows": 2}),
            "allergies": forms.Textarea(attrs={"rows": 2}),
            "conditions_medicales": forms.Textarea(attrs={"rows": 2}),
            "observations": forms.Textarea(attrs={"rows": 3}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp", "data-image-input": ""}),
        }
