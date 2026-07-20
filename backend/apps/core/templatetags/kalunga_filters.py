"""Template filters for French date formatting."""

from django import template
from django.utils import timezone

register = template.Library()

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
