"""Communication forms."""

from django import forms

from apps.secretariat.models import (
    Communication,
    CommunicationTarget,
    Enrollment,
    SchoolClass,
    Student,
)

from .academic import StyledModelForm

AUDIENCE_CHOICES = (
    (CommunicationTarget.TargetType.ALL_PARENTS, "Tous les parents (toutes les classes)"),
    (CommunicationTarget.TargetType.CLASS, "Une classe spécifique"),
    (CommunicationTarget.TargetType.STUDENT, "Un élève seulement"),
)

STATUS_EDIT_CHOICES = (
    (Communication.Status.DRAFT, "Brouillon"),
    (Communication.Status.PUBLISHED, "Publiée"),
)


def students_in_class(school_class: SchoolClass):
    return (
        Student.objects.filter(
            is_active=True,
            is_archived=False,
            enrollments__school_class=school_class,
            enrollments__status=Enrollment.Status.VALIDATED,
        )
        .distinct()
        .order_by("nom", "postnom", "prenom")
    )


def _student_label(obj: Student) -> str:
    return (
        f"{obj.matricule} — {obj.nom}"
        f"{(' ' + obj.postnom) if obj.postnom else ''} {obj.prenom}"
    )


class CommunicationForm(StyledModelForm):
    target_type = forms.ChoiceField(
        label="Destinataires",
        choices=AUDIENCE_CHOICES,
        help_text="Qui doit recevoir cette communication.",
    )
    school_class = forms.ModelChoiceField(
        label="Classe",
        queryset=SchoolClass.objects.none(),
        required=False,
        help_text="Pour un élève, choisissez d'abord sa classe.",
    )
    student = forms.ModelChoiceField(
        label="Élève",
        queryset=Student.objects.none(),
        required=False,
        help_text="Uniquement les élèves de la classe sélectionnée.",
    )
    status = forms.ChoiceField(
        label="Statut",
        choices=STATUS_EDIT_CHOICES,
        required=False,
        help_text="Brouillon pour préparer, Publiée pour diffuser.",
    )

    class Meta:
        model = Communication
        fields = ("title", "content", "category", "priority", "expires_at", "attachment")
        labels = {
            "title": "Titre",
            "content": "Contenu",
            "category": "Catégorie",
            "priority": "Priorité",
            "expires_at": "Date d'expiration",
            "attachment": "Pièce jointe",
        }
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
            "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, year=None, include_status=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.year = year
        if year:
            self.fields["school_class"].queryset = (
                SchoolClass.objects.filter(academic_year=year, is_active=True)
                .select_related("level", "section", "option")
                .order_by("level__order", "name")
            )
        else:
            self.fields["school_class"].queryset = SchoolClass.objects.filter(is_active=True)

        self.fields["student"].queryset = Student.objects.none()
        self.fields["student"].label_from_instance = _student_label

        if include_status:
            self.fields["status"].required = True
            if self.instance and self.instance.pk:
                self.fields["status"].initial = (
                    self.instance.status
                    if self.instance.status in {c[0] for c in STATUS_EDIT_CHOICES}
                    else Communication.Status.DRAFT
                )
        else:
            self.fields.pop("status", None)

        selected_class = None
        selected_student = None
        if self.instance and self.instance.pk:
            target = self.instance.targets.first()
            if target:
                if target.target_type in dict(AUDIENCE_CHOICES):
                    self.fields["target_type"].initial = target.target_type
                if target.school_class_id:
                    selected_class = target.school_class
                    self.fields["school_class"].initial = target.school_class_id
                if target.student_id:
                    selected_student = target.student
                    self.fields["student"].initial = target.student_id
                    if selected_class is None and year:
                        enrollment = (
                            Enrollment.objects.filter(
                                student_id=target.student_id,
                                academic_year=year,
                                status=Enrollment.Status.VALIDATED,
                            )
                            .select_related("school_class")
                            .first()
                        )
                        if enrollment:
                            selected_class = enrollment.school_class
                            self.fields["school_class"].initial = enrollment.school_class_id

        class_id = None
        if self.is_bound:
            class_id = self.data.get(self.add_prefix("school_class"))
        elif selected_class is not None:
            class_id = selected_class.pk

        if class_id:
            school_class = self.fields["school_class"].queryset.filter(pk=class_id).first()
            if school_class:
                self.fields["student"].queryset = students_in_class(school_class)

        for name in ("school_class", "student"):
            self.fields[name].widget.attrs["data-audience-field"] = name
        self.fields["school_class"].widget.attrs["data-audience-class"] = "1"
        self.fields["student"].widget.attrs["data-audience-student"] = "1"
        self.fields["target_type"].widget.attrs["data-audience-type"] = "1"

        self.order_fields(
            [
                "title",
                "content",
                "category",
                "priority",
                "status",
                "target_type",
                "school_class",
                "student",
                "expires_at",
                "attachment",
            ]
        )

    def clean(self):
        cleaned = super().clean()
        target_type = cleaned.get("target_type")
        school_class = cleaned.get("school_class")
        student = cleaned.get("student")

        if target_type == CommunicationTarget.TargetType.CLASS and not school_class:
            self.add_error("school_class", "Choisissez la classe destinataire.")
        if target_type == CommunicationTarget.TargetType.STUDENT:
            if not school_class:
                self.add_error("school_class", "Choisissez d'abord la classe de l'élève.")
            if not student:
                self.add_error("student", "Choisissez l'élève destinataire.")
            if school_class and student and not Enrollment.objects.filter(
                student=student,
                school_class=school_class,
                status=Enrollment.Status.VALIDATED,
            ).exists():
                self.add_error("student", "Cet élève n'est pas inscrit dans la classe sélectionnée.")
        if target_type == CommunicationTarget.TargetType.CLASS and school_class and self.year:
            if school_class.academic_year_id != self.year.pk:
                self.add_error(
                    "school_class",
                    "La classe doit appartenir à l'année scolaire sélectionnée.",
                )
        return cleaned

    def build_target(self) -> dict:
        target_type = self.cleaned_data["target_type"]
        target = {"target_type": target_type}
        if target_type == CommunicationTarget.TargetType.CLASS:
            target["school_class"] = self.cleaned_data["school_class"]
        elif target_type == CommunicationTarget.TargetType.STUDENT:
            target["student"] = self.cleaned_data["student"]
        return target


class CommunicationPublishForm(forms.Form):
    target_type = forms.ChoiceField(label="Publier pour", choices=AUDIENCE_CHOICES)
    school_class = forms.ModelChoiceField(
        label="Classe",
        queryset=SchoolClass.objects.none(),
        required=False,
        help_text="Pour un élève, choisissez d'abord sa classe.",
    )
    student = forms.ModelChoiceField(
        label="Élève",
        queryset=Student.objects.none(),
        required=False,
        help_text="Uniquement les élèves de la classe sélectionnée.",
    )

    def __init__(self, *args, year=None, initial_target=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.year = year
        if year:
            self.fields["school_class"].queryset = (
                SchoolClass.objects.filter(academic_year=year, is_active=True)
                .select_related("level", "section")
                .order_by("level__order", "name")
            )

        self.fields["student"].queryset = Student.objects.none()
        self.fields["student"].label_from_instance = _student_label

        selected_class = None
        if initial_target:
            if initial_target.target_type in dict(AUDIENCE_CHOICES):
                self.fields["target_type"].initial = initial_target.target_type
            if initial_target.school_class_id:
                selected_class = initial_target.school_class
                self.fields["school_class"].initial = initial_target.school_class_id
            if initial_target.student_id:
                self.fields["student"].initial = initial_target.student_id
                if selected_class is None and year:
                    enrollment = (
                        Enrollment.objects.filter(
                            student_id=initial_target.student_id,
                            academic_year=year,
                            status=Enrollment.Status.VALIDATED,
                        )
                        .select_related("school_class")
                        .first()
                    )
                    if enrollment:
                        selected_class = enrollment.school_class
                        self.fields["school_class"].initial = enrollment.school_class_id

        class_id = self.data.get("school_class") if self.is_bound else (
            selected_class.pk if selected_class is not None else None
        )
        if class_id:
            school_class = self.fields["school_class"].queryset.filter(pk=class_id).first()
            if school_class:
                self.fields["student"].queryset = students_in_class(school_class)

        for name in ("school_class", "student"):
            self.fields[name].widget.attrs["data-audience-field"] = name
            self.fields[name].widget.attrs["class"] = "form-select"
        self.fields["school_class"].widget.attrs["data-audience-class"] = "1"
        self.fields["student"].widget.attrs["data-audience-student"] = "1"
        self.fields["target_type"].widget.attrs["data-audience-type"] = "1"
        self.fields["target_type"].widget.attrs["class"] = "form-select"

    def clean(self):
        cleaned = super().clean()
        target_type = cleaned.get("target_type")
        school_class = cleaned.get("school_class")
        student = cleaned.get("student")
        if target_type == CommunicationTarget.TargetType.CLASS and not school_class:
            self.add_error("school_class", "Choisissez la classe destinataire.")
        if target_type == CommunicationTarget.TargetType.STUDENT:
            if not school_class:
                self.add_error("school_class", "Choisissez d'abord la classe de l'élève.")
            if not student:
                self.add_error("student", "Choisissez l'élève destinataire.")
            if school_class and student and not Enrollment.objects.filter(
                student=student,
                school_class=school_class,
                status=Enrollment.Status.VALIDATED,
            ).exists():
                self.add_error("student", "Cet élève n'est pas inscrit dans la classe sélectionnée.")
        return cleaned

    def build_target(self) -> dict:
        target_type = self.cleaned_data["target_type"]
        target = {"target_type": target_type}
        if target_type == CommunicationTarget.TargetType.CLASS:
            target["school_class"] = self.cleaned_data["school_class"]
        elif target_type == CommunicationTarget.TargetType.STUDENT:
            target["student"] = self.cleaned_data["student"]
        return target
