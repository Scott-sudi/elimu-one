"""Payment forms."""

from django import forms

from apps.finance.models import Payment, SchoolFee
from apps.finance.services.payment_sequence_service import (
    build_payable_fee_groups,
    fee_period_short_label,
)


def _style_fields(form: forms.Form) -> None:
    for field in form.fields.values():
        if isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
            continue
        css = "form-select" if isinstance(field.widget, forms.Select) else "form-input"
        field.widget.attrs.setdefault("class", css)


class PaymentForm(forms.Form):
    """Fast payment: matricule + fee name + period (month/tranche) + amount + mode."""

    matricule_suffix = forms.CharField(
        label="N° matricule",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "inputmode": "numeric",
                "data-payment-matricule": "1",
            }
        ),
    )
    fee_group = forms.ChoiceField(
        label="Frais",
        choices=[],
    )
    fee = forms.ModelChoiceField(
        label="Mois / tranche",
        queryset=SchoolFee.objects.none(),
        empty_label="Choisir…",
        required=False,
    )
    amount = forms.DecimalField(
        label="Montant payé",
        min_value=0.01,
        max_digits=14,
        decimal_places=2,
        required=False,
        help_text="Laisser vide pour payer le reste dû de la période ouverte.",
    )
    payment_method = forms.ChoiceField(
        label="Mode de paiement",
        choices=Payment.PaymentMethod.choices,
        initial=Payment.PaymentMethod.CASH,
    )

    def __init__(self, *args, fees=None, **kwargs):
        super().__init__(*args, **kwargs)
        fees = list(fees or [])
        self.fee_groups = build_payable_fee_groups(fees)
        self._groups_by_key = {g["key"]: g for g in self.fee_groups}

        self.fields["fee_group"].choices = [("", "Choisir…")] + [
            (g["key"], g["label"]) for g in self.fee_groups
        ]
        fee_ids = [fee.pk for fee in fees]
        self.fields["fee"].queryset = (
            SchoolFee.objects.filter(pk__in=fee_ids)
            .select_related("category")
            .order_by("category__order", "group_key", "period_index", "due_date", "code")
            if fee_ids
            else SchoolFee.objects.none()
        )
        self.fields["fee"].label_from_instance = fee_period_short_label
        self.fields["fee"].widget.attrs["data-payment-period"] = "1"
        self.fields["fee_group"].widget.attrs["data-payment-fee-group"] = "1"
        _style_fields(self)

    def clean_matricule_suffix(self):
        return (self.cleaned_data.get("matricule_suffix") or "").strip()

    def clean(self):
        cleaned = super().clean()
        group_key = cleaned.get("fee_group")
        fee = cleaned.get("fee")
        group = self._groups_by_key.get(group_key) if group_key else None
        if not group:
            self.add_error("fee_group", "Choisissez un frais.")
            return cleaned

        mode = group["schedule_mode"]
        group_fees = group["fees"]
        if mode == SchoolFee.ScheduleMode.ONCE:
            cleaned["fee"] = group_fees[0]
            return cleaned

        if fee is None:
            self.add_error(
                "fee",
                "Choisissez le mois."
                if mode == SchoolFee.ScheduleMode.MONTHS
                else "Choisissez la tranche.",
            )
            return cleaned

        allowed_ids = {f.pk for f in group_fees}
        if fee.pk not in allowed_ids:
            self.add_error("fee", "Cette période ne correspond pas au frais choisi.")
            return cleaned
        return cleaned
