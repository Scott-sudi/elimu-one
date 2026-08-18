"""Discipline forms."""

from __future__ import annotations

from django import forms

from apps.discipline.models import (
    AbsenceJustification,
    AttendanceScanEvent,
    AttendanceSchedule,
    ClassAttendanceSheet,
    DailyAttendance,
    DisciplinaryIncident,
    DisciplinaryMeasure,
    DisciplinaryMeasureType,
    ExitAuthorization,
    ParentSummons,
    StudentAttendanceRecord,
)
from apps.secretariat.models import Enrollment, SchoolClass, Student


class QrPointageForm(forms.Form):
    qr = forms.CharField(label="QR", max_length=255)
    operation = forms.ChoiceField(
        label="Opération",
        choices=(("arrivee", "Arrivée"),),
        initial="arrivee",
        required=False,
    )


class ManualAttendanceForm(forms.Form):
    enrollment_id = forms.UUIDField(label="Inscription")
    status = forms.ChoiceField(label="Statut", choices=DailyAttendance.Status.choices)
    note = forms.CharField(label="Observation", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, academic_year=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.academic_year = academic_year

    def clean_enrollment_id(self):
        public_id = self.cleaned_data["enrollment_id"]
        qs = Enrollment.objects.select_related("student", "school_class", "academic_year")
        if self.academic_year is not None:
            qs = qs.filter(academic_year=self.academic_year)
        enrollment = qs.filter(public_id=public_id).first()
        if not enrollment:
            raise forms.ValidationError("Inscription introuvable pour l'année sélectionnée.")
        if enrollment.status != Enrollment.Status.VALIDATED:
            raise forms.ValidationError("Inscription non validée.")
        return enrollment


class DailyAttendanceFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Élève")
    school_class = forms.UUIDField(required=False, label="Classe")
    status = forms.ChoiceField(
        required=False,
        choices=(("", "Tous les statuts"), *DailyAttendance.Status.choices),
    )
    date = forms.DateField(required=False, label="Date", widget=forms.DateInput(attrs={"type": "date"}))

    def class_queryset(self, academic_year):
        return SchoolClass.objects.filter(academic_year=academic_year, is_active=True).order_by("name")


class ClassFilterForm(forms.Form):
    q = forms.CharField(required=False)


class FolderFilterForm(forms.Form):
    q_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    month = forms.CharField(required=False)
    status = forms.ChoiceField(
        required=False,
        choices=(("", "Tous les statuts"), *ClassAttendanceSheet.Status.choices),
    )


class StudentFilterForm(forms.Form):
    q = forms.CharField(required=False)
    school_class = forms.UUIDField(required=False)


MONTH_FILTER_CHOICES = [
    ("", "Tous les mois"),
    ("1", "Janvier"),
    ("2", "Février"),
    ("3", "Mars"),
    ("4", "Avril"),
    ("5", "Mai"),
    ("6", "Juin"),
    ("7", "Juillet"),
    ("8", "Août"),
    ("9", "Septembre"),
    ("10", "Octobre"),
    ("11", "Novembre"),
    ("12", "Décembre"),
]


class IncidentFilterForm(forms.Form):
    """Triage incidents by calendar date parts, level and option."""

    year = forms.IntegerField(required=False, label="Année")
    month = forms.ChoiceField(
        required=False,
        label="Mois",
        choices=MONTH_FILTER_CHOICES,
    )
    day = forms.IntegerField(
        required=False,
        label="Jour",
        min_value=1,
        max_value=31,
    )
    level = forms.UUIDField(required=False, label="Niveau")
    option = forms.UUIDField(required=False, label="Option")

    def clean_month(self):
        raw = self.cleaned_data.get("month") or ""
        return str(raw).strip()


class IncidentForm(forms.ModelForm):
    """Create an incident from matricule (class auto-resolved), optional measure."""

    matricule = forms.CharField(
        label="Élève",
        max_length=64,
        help_text="Saisissez le matricule de l'élève.",
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Matricule",
                "autocomplete": "off",
                "data-matricule-input": "1",
            }
        ),
    )
    school_class_display = forms.CharField(
        label="Classe",
        required=False,
        help_text="Remplie automatiquement à partir du matricule.",
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "readonly": True,
                "placeholder": "Classe de l'élève",
                "data-class-input": "1",
            }
        ),
    )
    measure_type = forms.ModelChoiceField(
        label="Mesure disciplinaire",
        required=False,
        queryset=DisciplinaryMeasureType.objects.none(),
        empty_label="Aucune mesure",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Optionnel : enregistrer la mesure en même temps que l'incident.",
    )
    measure_description = forms.CharField(
        label="Détail de la mesure",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-input"}),
    )
    measure_start_date = forms.DateField(
        label="Début de la mesure",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
    )
    measure_end_date = forms.DateField(
        label="Fin de la mesure",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
    )
    measure_status = forms.ChoiceField(
        label="Statut de la mesure",
        required=False,
        choices=[("", "—")] + list(DisciplinaryMeasure.Status.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = DisciplinaryIncident
        fields = [
            "category",
            "title",
            "description",
            "incident_time",
            "location",
            "severity",
            "status",
            "witnesses",
            "immediate_action",
            "needs_summons",
        ]
        labels = {
            "category": "Catégorie",
            "title": "Titre",
            "description": "Description",
            "incident_time": "Heure",
            "location": "Lieu",
            "severity": "Gravité",
            "status": "Statut",
            "witnesses": "Témoins",
            "immediate_action": "Action immédiate",
            "needs_summons": "Nécessite une convocation",
        }
        widgets = {
            "incident_time": forms.TimeInput(attrs={"type": "time", "class": "form-input"}),
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "Résumé de l'incident"}),
            "location": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex. cour, salle 3…"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "witnesses": forms.Textarea(attrs={"rows": 2, "class": "form-input"}),
            "immediate_action": forms.Textarea(attrs={"rows": 2, "class": "form-input"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "severity": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    MEASURE_FIELD_NAMES = (
        "measure_type",
        "measure_description",
        "measure_start_date",
        "measure_end_date",
        "measure_status",
    )

    def __init__(self, *args, academic_year=None, include_measure=True, **kwargs):
        from apps.discipline.models import ConductCategory

        super().__init__(*args, **kwargs)
        self.academic_year = academic_year
        self.include_measure = include_measure
        self._resolved = None
        self.fields["category"].queryset = ConductCategory.objects.filter(
            is_active=True,
            is_archived=False,
        ).order_by("observation_type", "name")
        self.fields["category"].empty_label = "Choisir une catégorie"
        self.fields["measure_type"].queryset = DisciplinaryMeasureType.objects.filter(
            is_active=True,
            is_archived=False,
        ).order_by("name")
        if not include_measure:
            for name in self.MEASURE_FIELD_NAMES:
                self.fields.pop(name, None)
        if not self.is_bound:
            self.fields["severity"].initial = DisciplinaryIncident.Severity.MODERATE
            self.fields["status"].initial = DisciplinaryIncident.Status.REPORTED
            if include_measure and "measure_status" in self.fields:
                self.fields["measure_status"].initial = DisciplinaryMeasure.Status.PROPOSED
        order = [
            "matricule",
            "school_class_display",
            "category",
            "title",
            "description",
            "incident_time",
            "location",
            "severity",
            "status",
            "witnesses",
            "immediate_action",
            "needs_summons",
        ]
        if include_measure:
            order.extend(self.MEASURE_FIELD_NAMES)
        self.order_fields(order)

    def clean_matricule(self):
        from apps.discipline.services.exceptions import DisciplineError
        from apps.discipline.services.student_identity_service import resolve_student_identity

        raw = (self.cleaned_data.get("matricule") or "").strip()
        if not raw:
            raise forms.ValidationError("Indiquez le matricule de l'élève.")
        if self.academic_year is None:
            raise forms.ValidationError("Aucune année scolaire sélectionnée.")
        try:
            self._resolved = resolve_student_identity(
                academic_year=self.academic_year,
                identifier=raw,
            )
        except DisciplineError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return self._resolved.student.matricule

    def clean(self):
        cleaned = super().clean()
        if self._resolved is not None:
            cleaned["student"] = self._resolved.student
            cleaned["school_class"] = self._resolved.enrollment.school_class
            cleaned["school_class_display"] = self._resolved.enrollment.school_class.name
        return cleaned

    def save(self, commit=True):
        from django.utils import timezone

        instance = super().save(commit=False)
        if self._resolved is not None:
            instance.student = self._resolved.student
            instance.school_class = self._resolved.enrollment.school_class
        if not instance.incident_date:
            instance.incident_date = timezone.localdate()
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def create_linked_measure(self, *, incident, actor=None):
        """Create optional disciplinary measure attached to the incident."""
        if not self.include_measure:
            return None
        measure_type = self.cleaned_data.get("measure_type")
        if not measure_type:
            return None
        status = self.cleaned_data.get("measure_status") or DisciplinaryMeasure.Status.PROPOSED
        return DisciplinaryMeasure.objects.create(
            incident=incident,
            student=incident.student,
            measure_type=measure_type,
            description=self.cleaned_data.get("measure_description") or "",
            start_date=self.cleaned_data.get("measure_start_date"),
            end_date=self.cleaned_data.get("measure_end_date"),
            status=status,
            reason=incident.title,
            applied_by=actor,
        )


class MeasureForm(forms.ModelForm):
    class Meta:
        model = DisciplinaryMeasure
        fields = [
            "incident",
            "student",
            "measure_type",
            "description",
            "start_date",
            "end_date",
            "status",
            "reason",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 2}),
            "reason": forms.Textarea(attrs={"rows": 2}),
        }


class SummonsForm(forms.ModelForm):
    """Create a parent summons from matricule + optional incident title (text)."""

    matricule = forms.CharField(
        label="Élève",
        max_length=64,
        help_text="Saisissez le matricule de l'élève.",
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Matricule",
                "autocomplete": "off",
                "data-matricule-input": "1",
            }
        ),
    )
    school_class_display = forms.CharField(
        label="Classe",
        required=False,
        help_text="Remplie automatiquement à partir du matricule.",
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "readonly": True,
                "placeholder": "Classe de l'élève",
                "data-class-input": "1",
            }
        ),
    )
    incident_title = forms.CharField(
        label="Incident lié",
        required=False,
        max_length=180,
        help_text="Optionnel : saisissez le titre de l'incident (texte libre).",
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Titre de l'incident",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = ParentSummons
        fields = [
            "reason",
            "description",
            "summon_time",
            "location",
            "status",
            "delivery_mode",
            "next_action",
            "followup_date",
        ]
        labels = {
            "reason": "Motif",
            "description": "Description",
            "summon_time": "Heure",
            "location": "Lieu",
            "status": "Statut",
            "delivery_mode": "Mode de remise",
            "next_action": "Prochaine action",
            "followup_date": "Date de suivi",
        }
        widgets = {
            "summon_time": forms.TimeInput(attrs={"type": "time", "class": "form-input"}),
            "followup_date": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "reason": forms.TextInput(attrs={"class": "form-input", "placeholder": "Motif de la convocation"}),
            "location": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex. secrétariat, bureau…"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "next_action": forms.Textarea(attrs={"rows": 2, "class": "form-input"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "delivery_mode": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, academic_year=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.academic_year = academic_year
        self._resolved = None
        self._linked_incident = None
        if not self.is_bound:
            self.fields["status"].initial = ParentSummons.Status.SCHEDULED
            self.fields["delivery_mode"].initial = ParentSummons.DeliveryMode.PAPER
        self.order_fields(
            [
                "matricule",
                "school_class_display",
                "incident_title",
                "reason",
                "description",
                "summon_time",
                "location",
                "status",
                "delivery_mode",
                "next_action",
                "followup_date",
            ]
        )

    def clean_matricule(self):
        from apps.discipline.services.exceptions import DisciplineError
        from apps.discipline.services.student_identity_service import resolve_student_identity

        raw = (self.cleaned_data.get("matricule") or "").strip()
        if not raw:
            raise forms.ValidationError("Indiquez le matricule de l'élève.")
        if self.academic_year is None:
            raise forms.ValidationError("Aucune année scolaire sélectionnée.")
        try:
            self._resolved = resolve_student_identity(
                academic_year=self.academic_year,
                identifier=raw,
            )
        except DisciplineError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return self._resolved.student.matricule

    def clean_incident_title(self):
        return (self.cleaned_data.get("incident_title") or "").strip()

    def clean(self):
        cleaned = super().clean()
        if self._resolved is not None:
            cleaned["student"] = self._resolved.student
            cleaned["school_class_display"] = self._resolved.enrollment.school_class.name
            title = cleaned.get("incident_title") or ""
            if title:
                incident = (
                    DisciplinaryIncident.objects.filter(
                        academic_year=self.academic_year,
                        student=self._resolved.student,
                        title__iexact=title,
                    )
                    .order_by("-incident_date", "-created_at")
                    .first()
                )
                if incident is None:
                    incident = (
                        DisciplinaryIncident.objects.filter(
                            academic_year=self.academic_year,
                            student=self._resolved.student,
                            title__icontains=title,
                        )
                        .order_by("-incident_date", "-created_at")
                        .first()
                    )
                if incident is not None:
                    self._linked_incident = incident
                    cleaned["incident"] = incident
        return cleaned

    def save(self, commit=True):
        from django.utils import timezone

        instance = super().save(commit=False)
        if self._resolved is not None:
            instance.student = self._resolved.student
        if self._linked_incident is not None:
            instance.incident = self._linked_incident
        if not instance.summon_date:
            instance.summon_date = timezone.localdate()
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ExitAuthorizationForm(forms.ModelForm):
    """Create an exit authorization from matricule (enrollment auto-resolved)."""

    matricule = forms.CharField(
        label="Élève",
        max_length=64,
        help_text="Saisissez le matricule de l'élève.",
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Matricule",
                "autocomplete": "off",
                "data-matricule-input": "1",
            }
        ),
    )
    school_class_display = forms.CharField(
        label="Classe",
        required=False,
        help_text="Remplie automatiquement à partir du matricule.",
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "readonly": True,
                "placeholder": "Classe de l'élève",
                "data-class-input": "1",
            }
        ),
    )

    class Meta:
        model = ExitAuthorization
        fields = [
            "planned_exit_time",
            "expected_return_time",
            "reason",
            "requesting_guardian",
            "guardian_contact",
            "status",
            "note",
        ]
        labels = {
            "planned_exit_time": "Heure de sortie prévue",
            "expected_return_time": "Heure de retour prévue",
            "reason": "Motif",
            "requesting_guardian": "Responsable demandeur",
            "guardian_contact": "Contact du responsable",
            "status": "Statut",
            "note": "Observation",
        }
        widgets = {
            "planned_exit_time": forms.TimeInput(attrs={"type": "time", "class": "form-input"}),
            "expected_return_time": forms.TimeInput(attrs={"type": "time", "class": "form-input"}),
            "reason": forms.Textarea(attrs={"rows": 3, "class": "form-input"}),
            "requesting_guardian": forms.TextInput(attrs={"class": "form-input"}),
            "guardian_contact": forms.TextInput(attrs={"class": "form-input"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "note": forms.Textarea(attrs={"rows": 2, "class": "form-input"}),
        }

    def __init__(self, *args, academic_year=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.academic_year = academic_year
        self._resolved = None
        if not self.is_bound:
            self.fields["status"].initial = ExitAuthorization.Status.AUTHORIZED
        self.order_fields(
            [
                "matricule",
                "school_class_display",
                "planned_exit_time",
                "expected_return_time",
                "reason",
                "requesting_guardian",
                "guardian_contact",
                "status",
                "note",
            ]
        )

    def clean_matricule(self):
        from apps.discipline.services.exceptions import DisciplineError
        from apps.discipline.services.student_identity_service import resolve_student_identity

        raw = (self.cleaned_data.get("matricule") or "").strip()
        if not raw:
            raise forms.ValidationError("Indiquez le matricule de l'élève.")
        if self.academic_year is None:
            raise forms.ValidationError("Aucune année scolaire sélectionnée.")
        try:
            self._resolved = resolve_student_identity(
                academic_year=self.academic_year,
                identifier=raw,
            )
        except DisciplineError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return self._resolved.student.matricule

    def clean(self):
        cleaned = super().clean()
        if self._resolved is not None:
            cleaned["student"] = self._resolved.student
            cleaned["enrollment"] = self._resolved.enrollment
            cleaned["school_class_display"] = self._resolved.enrollment.school_class.name
        return cleaned

    def save(self, commit=True):
        from django.utils import timezone

        instance = super().save(commit=False)
        if self._resolved is not None:
            instance.student = self._resolved.student
            instance.enrollment = self._resolved.enrollment
        if not instance.date:
            instance.date = timezone.localdate()
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class AttendanceRecordCorrectionForm(forms.Form):
    status = forms.ChoiceField(
        choices=(
            (StudentAttendanceRecord.Status.PRESENT, "Présent"),
            (StudentAttendanceRecord.Status.ABSENT, "Absent"),
            (StudentAttendanceRecord.Status.UNMARKED, "Non marqué"),
        )
    )
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))
    password = forms.CharField(widget=forms.PasswordInput())


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

