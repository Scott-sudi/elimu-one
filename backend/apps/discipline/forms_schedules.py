"""Vacation schedule form (separate from large forms.py for safe deploy)."""

from __future__ import annotations

from django import forms

from apps.discipline.models import AttendanceSchedule
from apps.secretariat.models import SchoolClass


class VacationScheduleForm(forms.Form):
    """Configure start / grace / end times and class assignment for one vacation."""

    vacation = forms.ChoiceField(
        choices=AttendanceSchedule.Vacation.choices,
        widget=forms.HiddenInput,
    )
    start_time = forms.TimeField(
        label="Début des cours",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-input"}),
    )
    present_until = forms.TimeField(
        label="Présent jusqu'à",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-input"}),
        help_text="Après cette heure, l'élève est marqué en retard.",
    )
    end_time = forms.TimeField(
        label="Fin des cours",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-input"}),
        help_text="Après cette heure, le pointage est refusé.",
    )
    school_classes = forms.ModelMultipleChoiceField(
        label="Classes concernées",
        queryset=SchoolClass.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, academic_year=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.academic_year = academic_year
        qs = SchoolClass.objects.none()
        if academic_year is not None:
            qs = SchoolClass.objects.filter(academic_year=academic_year, is_active=True).order_by(
                "level__order", "name"
            )
        self.fields["school_classes"].queryset = qs
        for name in ("start_time", "present_until", "end_time"):
            self.fields[name].widget.attrs.setdefault("class", "form-input")

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        present_until = cleaned.get("present_until")
        end = cleaned.get("end_time")
        if start and present_until and present_until < start:
            self.add_error("present_until", "Doit être après le début des cours.")
        if present_until and end and end <= present_until:
            self.add_error("end_time", "Doit être après « Présent jusqu'à ».")
        return cleaned
