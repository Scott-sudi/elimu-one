"""Guardian forms."""

from django import forms

from apps.secretariat.models import Guardian, StudentGuardian
from apps.secretariat.services.exceptions import SecretariatError
from apps.secretariat.services.guardian_service import assert_accepted_phone_format

from .academic import StyledModelForm


class GuardianForm(StyledModelForm):
    class Meta:
        model = Guardian
        exclude = (
            "numero_identification",
            "is_archived",
            "is_active",
            "created_at",
            "updated_at",
            "public_id",
        )
        labels = {
            "nom": "Nom",
            "postnom": "Postnom",
            "prenom": "Prénom",
            "sexe": "Sexe",
            "telephone_principal": "Téléphone principal",
            "telephone_secondaire": "Téléphone secondaire",
            "email": "Adresse e-mail",
            "adresse": "Adresse",
            "profession": "Profession",
        }
        help_texts = {
            "telephone_principal": "Ex. 0990123456 ou +243990123456",
            "telephone_secondaire": "Optionnel — même format que le principal",
            "email": "Optionnel",
        }

    def clean_telephone_principal(self):
        value = self.cleaned_data.get("telephone_principal") or ""
        try:
            return assert_accepted_phone_format(value)
        except SecretariatError as exc:
            raise forms.ValidationError(str(exc)) from exc

    def clean_telephone_secondaire(self):
        value = (self.cleaned_data.get("telephone_secondaire") or "").strip()
        if not value:
            return ""
        try:
            return assert_accepted_phone_format(value)
        except SecretariatError as exc:
            raise forms.ValidationError(str(exc)) from exc

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip()


class StudentGuardianForm(StyledModelForm):
    class Meta:
        model = StudentGuardian
        fields = (
            "guardian",
            "lien_parente",
            "is_primary",
            "is_emergency_contact",
            "can_pickup",
            "receives_notifications",
            "lives_with_student",
            "observation",
        )
        labels = {
            "guardian": "Responsable",
            "lien_parente": "Lien de parenté",
            "is_primary": "Responsable principal",
            "is_emergency_contact": "Contact d'urgence",
            "can_pickup": "Autorisé à récupérer l'élève",
            "receives_notifications": "Reçoit les notifications",
            "lives_with_student": "Vit avec l'élève",
            "observation": "Observation",
        }
