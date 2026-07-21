"""Communication forms."""

from django import forms

from apps.secretariat.models import (
    AcademicYear,
    Communication,
    CommunicationTarget,
    Guardian,
    Option,
    SchoolClass,
    SchoolLevel,
    Section,
    Student,
)

from .academic import StyledModelForm


class CommunicationForm(StyledModelForm):
    target_type = forms.ChoiceField(label="Destinataires", choices=CommunicationTarget.TargetType.choices)
    academic_year = forms.ModelChoiceField(label="Année scolaire", queryset=AcademicYear.objects.all(), required=False)
    level = forms.ModelChoiceField(label="Niveau", queryset=SchoolLevel.objects.filter(is_active=True), required=False)
    section = forms.ModelChoiceField(label="Section", queryset=Section.objects.filter(is_active=True), required=False)
    option = forms.ModelChoiceField(label="Option", queryset=Option.objects.filter(is_active=True), required=False)
    school_class = forms.ModelChoiceField(label="Classe", queryset=SchoolClass.objects.filter(is_active=True), required=False)
    student = forms.ModelChoiceField(label="Élève", queryset=Student.objects.filter(is_active=True), required=False)
    guardian = forms.ModelChoiceField(label="Responsable", queryset=Guardian.objects.filter(is_active=True), required=False)

    class Meta:
        model = Communication
        fields = ("title", "content", "category", "priority", "expires_at", "attachment", "is_pinned")
        labels = {
            "title": "Titre", "content": "Contenu", "category": "Catégorie",
            "priority": "Priorité", "expires_at": "Date d'expiration",
            "attachment": "Pièce jointe", "is_pinned": "Épingler",
        }
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
            "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
