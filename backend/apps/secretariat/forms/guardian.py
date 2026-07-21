"""Guardian forms."""

from apps.secretariat.models import Guardian, StudentGuardian

from .academic import StyledModelForm


class GuardianForm(StyledModelForm):
    class Meta:
        model = Guardian
        exclude = ("is_archived", "created_at", "updated_at", "public_id")
        labels = {
            "nom": "Nom", "postnom": "Postnom", "prenom": "Prénom", "sexe": "Sexe",
            "telephone_principal": "Téléphone principal", "telephone_secondaire": "Téléphone secondaire",
            "email": "Adresse e-mail", "adresse": "Adresse", "profession": "Profession",
            "numero_identification": "Numéro d'identification", "is_active": "Actif",
        }


class StudentGuardianForm(StyledModelForm):
    class Meta:
        model = StudentGuardian
        fields = (
            "guardian", "lien_parente", "is_primary", "is_emergency_contact",
            "can_pickup", "receives_notifications", "lives_with_student", "observation",
        )
        labels = {
            "guardian": "Responsable", "lien_parente": "Lien de parenté",
            "is_primary": "Responsable principal", "is_emergency_contact": "Contact d'urgence",
            "can_pickup": "Autorisé à récupérer l'élève",
            "receives_notifications": "Reçoit les notifications",
            "lives_with_student": "Vit avec l'élève", "observation": "Observation",
        }
