"""School fee forms."""

from django import forms

from apps.finance.models import FeeAmountChangeRequest, FeeCategory, SchoolFee
from apps.secretariat.models import Option, SchoolClass, SchoolLevel, Section


def _style_fields(form: forms.Form) -> None:
    for field in form.fields.values():
        if isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
            continue
        if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
            css = "form-select"
        else:
            css = "form-input"
        field.widget.attrs.setdefault("class", css)


class SchoolFeeForm(forms.Form):
    """Create a school fee draft for the selected academic year."""

    SCOPE_ALL = "TOUTES"
    SCOPE_SPECIFIC = "SPECIFIQUE"
    SCOPE_CHOICES = (
        (SCOPE_ALL, "Toutes les classes"),
        (SCOPE_SPECIFIC, "Cible spécifique"),
    )
    SPECIFIC_TYPE_CHOICES = (
        (SchoolFee.ApplicationType.SELECTED_CLASSES, "Classe(s) sélectionnée(s)"),
        (SchoolFee.ApplicationType.LEVEL, "Niveau"),
        (SchoolFee.ApplicationType.SECTION, "Section"),
        (SchoolFee.ApplicationType.OPTION, "Option"),
    )

    category = forms.ModelChoiceField(
        label="Catégorie",
        queryset=FeeCategory.objects.none(),
        empty_label="Choisir…",
    )
    label = forms.CharField(label="Libellé", max_length=200)
    code = forms.CharField(label="Code", max_length=30)
    amount = forms.DecimalField(
        label="Montant",
        min_value=0.01,
        max_digits=14,
        decimal_places=2,
    )
    currency = forms.CharField(label="Devise", max_length=10, initial="CDF")
    due_date = forms.DateField(
        label="Date d'échéance",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    target_scope = forms.ChoiceField(
        label="Application",
        choices=SCOPE_CHOICES,
        initial=SCOPE_ALL,
    )
    application_type = forms.ChoiceField(
        label="Type de cible",
        choices=SPECIFIC_TYPE_CHOICES,
        initial=SchoolFee.ApplicationType.SELECTED_CLASSES,
        required=False,
    )
    is_mandatory = forms.BooleanField(label="Obligatoire", required=False, initial=True)
    allow_partial = forms.BooleanField(
        label="Paiement partiel autorisé",
        required=False,
        initial=True,
    )
    description = forms.CharField(
        label="Description",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    school_classes = forms.ModelMultipleChoiceField(
        label="Classes",
        queryset=SchoolClass.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6}),
    )
    levels = forms.ModelMultipleChoiceField(
        label="Niveaux",
        queryset=SchoolLevel.objects.filter(is_active=True).order_by("order", "name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 5}),
    )
    sections = forms.ModelMultipleChoiceField(
        label="Sections",
        queryset=Section.objects.filter(is_active=True).order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 5}),
    )
    options = forms.ModelMultipleChoiceField(
        label="Options",
        queryset=Option.objects.filter(is_active=True).select_related("section").order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 5}),
    )

    def __init__(self, *args, academic_year=None, categories=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.academic_year = academic_year
        if categories is not None:
            self.fields["category"].queryset = categories
        else:
            self.fields["category"].queryset = FeeCategory.objects.filter(
                is_active=True
            ).order_by("order", "name")
        if academic_year is not None:
            self.fields["school_classes"].queryset = (
                SchoolClass.objects.filter(academic_year=academic_year, is_active=True)
                .select_related("level", "section", "option")
                .order_by("level__order", "name")
            )
        _style_fields(self)

    def clean_code(self):
        return (self.cleaned_data.get("code") or "").strip().upper()

    def clean_label(self):
        return (self.cleaned_data.get("label") or "").strip()

    def clean_currency(self):
        return (self.cleaned_data.get("currency") or "CDF").strip().upper() or "CDF"

    def clean(self):
        cleaned = super().clean()
        scope = cleaned.get("target_scope") or self.SCOPE_ALL
        if scope == self.SCOPE_ALL:
            cleaned["application_type"] = SchoolFee.ApplicationType.ALL_CLASSES
            cleaned["school_classes"] = []
            cleaned["levels"] = []
            cleaned["sections"] = []
            cleaned["options"] = []
            return cleaned

        app_type = cleaned.get("application_type")
        if not app_type:
            self.add_error("application_type", "Choisissez le type de cible.")
            return cleaned
        if app_type == SchoolFee.ApplicationType.SELECTED_CLASSES and not cleaned.get(
            "school_classes"
        ):
            self.add_error("school_classes", "Sélectionnez au moins une classe.")
        elif app_type == SchoolFee.ApplicationType.LEVEL and not cleaned.get("levels"):
            self.add_error("levels", "Sélectionnez au moins un niveau.")
        elif app_type == SchoolFee.ApplicationType.SECTION and not cleaned.get("sections"):
            self.add_error("sections", "Sélectionnez au moins une section.")
        elif app_type == SchoolFee.ApplicationType.OPTION and not cleaned.get("options"):
            self.add_error("options", "Sélectionnez au moins une option.")
        return cleaned

    def service_kwargs(self) -> dict:
        data = self.cleaned_data
        return {
            "category": data["category"],
            "code": data["code"],
            "label": data["label"],
            "amount": data["amount"],
            "currency": data["currency"],
            "description": data.get("description") or "",
            "due_date": data.get("due_date"),
            "is_mandatory": bool(data.get("is_mandatory")),
            "allow_partial": bool(data.get("allow_partial")),
            "application_type": data["application_type"],
            "school_class_ids": [c.pk for c in data.get("school_classes") or []],
            "level_ids": [level.pk for level in data.get("levels") or []],
            "section_ids": [section.pk for section in data.get("sections") or []],
            "option_ids": [option.pk for option in data.get("options") or []],
        }


class ClassOtherFeeForm(forms.Form):
    """Create a class fee request with once / tranche / month schedule."""

    SCHEDULE_ONCE = SchoolFee.ScheduleMode.ONCE
    SCHEDULE_TRANCHES = SchoolFee.ScheduleMode.TRANCHES
    SCHEDULE_MONTHS = SchoolFee.ScheduleMode.MONTHS
    MONTH_ALL = "TOUS"
    MONTH_SELECTION = "SELECTION"

    code = forms.CharField(label="Code", max_length=20)
    label = forms.CharField(label="Nom du frais", max_length=200)
    amount = forms.DecimalField(
        label="Montant",
        min_value=0.01,
        max_digits=14,
        decimal_places=2,
        help_text="Montant par colonne (par tranche ou par mois selon le mode).",
    )
    description = forms.CharField(
        label="Motif",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    schedule_mode = forms.ChoiceField(
        label="Mode de paiement",
        choices=SchoolFee.ScheduleMode.choices,
        initial=SCHEDULE_ONCE,
    )
    tranche_count = forms.IntegerField(
        label="Nombre de tranches",
        min_value=2,
        max_value=12,
        required=False,
        initial=3,
    )
    month_scope = forms.ChoiceField(
        label="Période mensuelle",
        choices=(
            (MONTH_ALL, "Tous les mois de l'année scolaire"),
            (MONTH_SELECTION, "Mois spécifiques"),
        ),
        initial=MONTH_ALL,
        required=False,
    )
    months = forms.MultipleChoiceField(
        label="Mois",
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, academic_year=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.academic_year = academic_year
        month_choices = []
        if academic_year is not None:
            from apps.finance.services.fee_structure_service import (
                MONTH_LABELS_FR,
                iter_academic_months,
            )

            for month_start in iter_academic_months(academic_year):
                key = f"{month_start.year}-{month_start.month:02d}"
                month_label = f"{MONTH_LABELS_FR[month_start.month]} {month_start.year}"
                month_choices.append((key, month_label))
        self.fields["months"].choices = month_choices
        _style_fields(self)

    def clean_code(self):
        return (self.cleaned_data.get("code") or "").strip().upper()

    def clean_label(self):
        return (self.cleaned_data.get("label") or "").strip()

    def clean_description(self):
        return (self.cleaned_data.get("description") or "").strip()

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("schedule_mode") or self.SCHEDULE_ONCE
        if mode == self.SCHEDULE_TRANCHES:
            count = cleaned.get("tranche_count")
            if not count or count < 2:
                self.add_error("tranche_count", "Indiquez au moins 2 tranches.")
        elif mode == self.SCHEDULE_MONTHS:
            scope = cleaned.get("month_scope") or self.MONTH_ALL
            cleaned["month_scope"] = scope
            if scope == self.MONTH_SELECTION and not cleaned.get("months"):
                self.add_error("months", "Sélectionnez au moins un mois.")
        else:
            cleaned["schedule_mode"] = self.SCHEDULE_ONCE
        return cleaned


class FeeAmountChangeForm(forms.Form):
    """Propose a new amount for a fee period column."""

    fee_id = forms.UUIDField(widget=forms.HiddenInput)
    new_amount = forms.DecimalField(
        label="Nouveau montant",
        min_value=0.01,
        max_digits=14,
        decimal_places=2,
    )
    scope = forms.ChoiceField(
        label="Portée",
        choices=FeeAmountChangeRequest.Scope.choices,
        initial=FeeAmountChangeRequest.Scope.CURRENT_CLASS,
        widget=forms.RadioSelect,
    )
    target_classes = forms.ModelMultipleChoiceField(
        label="Classes concernées",
        queryset=SchoolClass.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    comment = forms.CharField(
        label="Commentaire",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, academic_year=None, **kwargs):
        super().__init__(*args, **kwargs)
        year = academic_year
        if year is not None:
            self.fields["target_classes"].queryset = (
                SchoolClass.objects.filter(academic_year=year, is_active=True)
                .select_related("level")
                .order_by("level__order", "name")
            )
        _style_fields(self)

    def clean(self):
        cleaned = super().clean()
        scope = cleaned.get("scope")
        if scope == FeeAmountChangeRequest.Scope.SELECTED_CLASSES:
            if not cleaned.get("target_classes"):
                self.add_error(
                    "target_classes",
                    "Sélectionnez au moins une classe.",
                )
        return cleaned
