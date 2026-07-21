"""Academic structure forms."""

from django import forms

from apps.secretariat.models import AcademicYear, Option, SchoolLevel, Section


class StyledModelForm(forms.ModelForm):
    """Apply the existing design-system classes to Django widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-input"
            field.widget.attrs.setdefault("class", css)


class AcademicYearForm(StyledModelForm):
    class Meta:
        model = AcademicYear
        fields = ("label", "start_date", "end_date", "is_active")
        labels = {"label": "Libellé", "start_date": "Date de début", "end_date": "Date de fin", "is_active": "Activer"}
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}


class SchoolLevelForm(StyledModelForm):
    class Meta:
        model = SchoolLevel
        fields = ("name", "code", "order", "description", "is_active")
        labels = {"name": "Nom", "code": "Code", "order": "Ordre", "description": "Description", "is_active": "Actif"}


class SectionForm(StyledModelForm):
    class Meta:
        model = Section
        fields = ("name", "code", "description", "is_active")
        labels = {"name": "Nom", "code": "Code", "description": "Description", "is_active": "Active"}


class OptionForm(StyledModelForm):
    class Meta:
        model = Option
        fields = ("name", "code", "section", "description", "is_active")
        labels = {"name": "Nom", "code": "Code", "section": "Section", "description": "Description", "is_active": "Active"}
