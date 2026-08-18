"""School class forms."""

from django import forms

from apps.secretariat.models import SchoolClass

from .academic import StyledModelForm


class SchoolClassForm(StyledModelForm):
    """Create form — academic_year is forced from session in the view."""

    letter = forms.ChoiceField(
        label="Lettre",
        choices=[("", "Choisir la lettre…")] + list(SchoolClass.LETTER_CHOICES),
        required=True,
        widget=forms.Select,
        help_text="Ex. : A, B, C ou D — deux classes du même niveau ne peuvent pas partager la même lettre.",
    )

    class Meta:
        model = SchoolClass
        fields = (
            "level",
            "section",
            "option",
            "letter",
            "name",
            "code",
            "max_capacity",
            "room",
            "description",
            "is_active",
        )
        labels = {
            "level": "Niveau",
            "section": "Section",
            "option": "Option",
            "letter": "Lettre",
            "name": "Nom",
            "code": "Code",
            "max_capacity": "Capacité maximale",
            "room": "Local",
            "description": "Description",
            "is_active": "Active",
        }

    def clean_letter(self):
        letter = (self.cleaned_data.get("letter") or "").strip().upper()
        if not letter:
            raise forms.ValidationError("Veuillez choisir la lettre de la classe.")
        allowed = {choice for choice, _ in SchoolClass.LETTER_CHOICES}
        if letter not in allowed:
            raise forms.ValidationError("Lettre de classe invalide.")
        return letter

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()
        if not code:
            raise forms.ValidationError("Le code de la classe est obligatoire.")
        return code

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Le nom de la classe est obligatoire.")
        return name


class SchoolClassUpdateForm(StyledModelForm):
    class Meta:
        model = SchoolClass
        fields = ("name", "max_capacity", "room", "is_active")
        labels = {
            "name": "Nom",
            "max_capacity": "Capacité maximale",
            "room": "Local",
            "is_active": "Active",
        }

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Le nom de la classe est obligatoire.")
        return name
