"""Enrollment workflow forms."""

from django import forms

from apps.secretariat.models import Enrollment, SchoolClass

from .academic import StyledModelForm


class EnrollmentForm(StyledModelForm):
    class Meta:
        model = Enrollment
        fields = ("student", "school_class", "enrollment_type", "enrollment_date", "status", "provenance", "observation")
        labels = {
            "student": "Élève", "school_class": "Classe", "enrollment_type": "Type d'inscription",
            "enrollment_date": "Date d'inscription", "status": "Statut",
            "provenance": "Provenance", "observation": "Observation",
        }
        widgets = {"enrollment_date": forms.DateInput(attrs={"type": "date"})}


class ReenrollmentForm(forms.Form):
    previous_enrollment = forms.ModelChoiceField(label="Inscription précédente", queryset=Enrollment.objects.all())
    target_class = forms.ModelChoiceField(label="Classe de destination", queryset=SchoolClass.objects.all())
    force_over_capacity = forms.BooleanField(label="Autoriser le dépassement de capacité", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-input"


class TransferForm(forms.Form):
    enrollment = forms.ModelChoiceField(label="Inscription", queryset=Enrollment.objects.filter(status=Enrollment.Status.VALIDATED))
    to_class = forms.ModelChoiceField(label="Classe de destination", queryset=SchoolClass.objects.filter(is_active=True))
    motif = forms.CharField(label="Motif", widget=forms.Textarea(attrs={"rows": 3}))
    transfer_date = forms.DateField(label="Date du transfert", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    force_over_capacity = forms.BooleanField(label="Autoriser le dépassement de capacité", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-input"
