"""Template filters for French date formatting and finance tones."""

from decimal import Decimal

from django import template
from django.utils import timezone

register = template.Library()

_PAYMENT_TONE_BY_STATUS = {
    "NON_PAYE": "unpaid",
    "PARTIEL": "partial",
    "PAYE": "paid",
    "EXONERE": "paid",
}

MONTHS_FR = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}


@register.filter
def date_fr(value):
    if not value:
        return "—"
    local = timezone.localtime(value) if timezone.is_aware(value) else value
    return f"{local.day} {MONTHS_FR[local.month]} {local.year}"


@register.filter
def datetime_fr(value):
    if not value:
        return "—"
    local = timezone.localtime(value) if timezone.is_aware(value) else value
    return f"{local.day} {MONTHS_FR[local.month]} {local.year} à {local.hour} h {local.minute:02d}"


@register.filter
def payment_tone(status):
    """Map obligation status to unpaid / partial / paid CSS tone."""
    if not status:
        return "unpaid"
    key = getattr(status, "value", None) or str(status)
    return _PAYMENT_TONE_BY_STATUS.get(key, "unpaid")


@register.filter
def payment_tone_from_amounts(amount_paid, amount_remaining=None):
    """
    Derive tone from paid/remaining amounts.
    Usage: {{ amount_paid|payment_tone_from_amounts:amount_remaining }}
    """
    paid = Decimal(str(amount_paid or 0))
    remaining = Decimal(str(amount_remaining or 0))
    if paid <= 0 and remaining > 0:
        return "unpaid"
    if remaining <= 0:
        return "paid"
    return "partial"
