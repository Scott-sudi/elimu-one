"""Enrollment workflow forms."""

from django import forms
from django.utils import timezone

from apps.secretariat.models import Enrollment, SchoolClass, Student

from .academic import StyledModelForm


def _style_form_fields(form: forms.Form) -> None:
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault("class", "form-check-input")
        elif isinstance(field.widget, forms.Select):
            field.widget.attrs.setdefault("class", "form-select")
        else:
            field.widget.attrs.setdefault("class", "form-input")


class EnrollmentForm(StyledModelForm):
    class Meta:
        model = Enrollment
        fields = (
            "student",
            "school_class",
            "enrollment_type",
            "enrollment_date",
            "status",
            "provenance",
            "observation",
        )
        labels = {
            "student": "Élève",
            "school_class": "Classe",
            "enrollment_type": "Type d'inscription",
            "enrollment_date": "Date d'inscription",
            "status": "Statut",
            "provenance": "Provenance",
            "observation": "Observation",
        }
        widgets = {"enrollment_date": forms.DateInput(attrs={"type": "date"})}


class ReenrollmentForm(forms.Form):
    previous_enrollment = forms.ModelChoiceField(
        label="Inscription précédente",
        queryset=Enrollment.objects.all(),
    )
    target_class = forms.ModelChoiceField(
        label="Classe de destination",
        queryset=SchoolClass.objects.all(),
    )
    force_over_capacity = forms.BooleanField(
        label="Autoriser le dépassement de capacité",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_form_fields(self)


class ClassNewStudentForm(StyledModelForm):
    """New student in a class — only guardian phone is required (must already exist)."""

    telephone_responsable = forms.CharField(
        label="Téléphone du responsable",
        max_length=30,
        help_text=(
            "Le responsable doit déjà exister (menu Responsables). "
            "S’il est trouvé, l’élève lui sera lié automatiquement."
        ),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "tel",
                "data-guardian-phone": "",
                "inputmode": "tel",
            }
        ),
    )
    provenance = forms.CharField(label="Provenance", required=False, max_length=255)
    observation = forms.CharField(
        label="Observation",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    class Meta:
        model = Student
        fields = (
            "nom",
            "postnom",
            "prenom",
            "sexe",
            "date_naissance",
            "lieu_naissance",
            "nationalite",
            "adresse",
            "photo",
            "ancien_etablissement",
            "date_admission",
            "groupe_sanguin",
            "allergies",
            "conditions_medicales",
            "observations",
        )
        labels = {
            "nom": "Nom",
            "postnom": "Postnom",
            "prenom": "Prénom",
            "sexe": "Sexe",
            "date_naissance": "Date de naissance",
            "lieu_naissance": "Lieu de naissance",
            "nationalite": "Nationalité",
            "adresse": "Adresse",
            "photo": "Photo",
            "ancien_etablissement": "Ancien établissement",
            "date_admission": "Date d'admission",
            "groupe_sanguin": "Groupe sanguin",
            "allergies": "Allergies",
            "conditions_medicales": "Conditions médicales",
            "observations": "Observations",
        }
        widgets = {
            "date_naissance": forms.DateInput(attrs={"type": "date"}),
            "date_admission": forms.DateInput(attrs={"type": "date"}),
            "adresse": forms.Textarea(attrs={"rows": 2}),
            "allergies": forms.Textarea(attrs={"rows": 2}),
            "conditions_medicales": forms.Textarea(attrs={"rows": 2}),
            "observations": forms.Textarea(attrs={"rows": 2}),
            "photo": forms.ClearableFileInput(
                attrs={
                    "accept": "image/jpeg,image/png,image/webp",
                    "data-image-input": "",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date_admission"].initial = timezone.localdate()
        _style_form_fields(self)
        self.order_fields(
            [
                "telephone_responsable",
                "nom",
                "postnom",
                "prenom",
                "sexe",
                "date_naissance",
                "lieu_naissance",
                "nationalite",
                "adresse",
                "photo",
                "ancien_etablissement",
                "date_admission",
                "groupe_sanguin",
                "allergies",
                "conditions_medicales",
                "observations",
                "provenance",
                "observation",
            ]
        )

    def clean_telephone_responsable(self):
        from apps.secretariat.services.exceptions import SecretariatError
        from apps.secretariat.services.guardian_service import require_existing_guardian_by_phone

        value = (self.cleaned_data.get("telephone_responsable") or "").strip()
        try:
            guardian = require_existing_guardian_by_phone(value)
        except SecretariatError as exc:
            raise forms.ValidationError(str(exc)) from exc
        self._resolved_guardian = guardian
        return guardian.telephone_principal

    def get_guardian(self):
        return getattr(self, "_resolved_guardian", None)


class ClassReenrollmentForm(forms.Form):
    previous_enrollment = forms.ModelChoiceField(
        label="Élève (année précédente)",
        queryset=Enrollment.objects.none(),
    )

    def __init__(self, *args, queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if queryset is not None:
            self.fields["previous_enrollment"].queryset = queryset
        self.fields["previous_enrollment"].label_from_instance = lambda obj: (
            f"{obj.student.matricule} — "
            f"{obj.student.nom}"
            f"{(' ' + obj.student.postnom) if obj.student.postnom else ''}"
            f" {obj.student.prenom} · {obj.school_class.name}"
        )
        _style_form_fields(self)


class TransferForm(forms.Form):
    enrollment = forms.ModelChoiceField(
        label="Inscription",
        queryset=Enrollment.objects.filter(status=Enrollment.Status.VALIDATED),
    )
    to_class = forms.ModelChoiceField(
        label="Classe de destination",
        queryset=SchoolClass.objects.filter(is_active=True),
    )
    motif = forms.CharField(label="Motif", widget=forms.Textarea(attrs={"rows": 3}))
    transfer_date = forms.DateField(
        label="Date du transfert",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    force_over_capacity = forms.BooleanField(
        label="Autoriser le dépassement de capacité",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_form_fields(self)
