"""Parse and apply BI GET filters — only fields supported by models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from django.db.models import QuerySet
from django.http import HttpRequest


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_int(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class BiFilters:
    """Normalized decision filters from request.GET."""

    date_from: date | None = None
    date_to: date | None = None
    level_id: int | None = None
    section_id: int | None = None
    option_id: int | None = None
    class_id: int | None = None
    gender: str | None = None  # Student.sexe (M/F/O)
    fee_id: int | None = None
    enrollment_status: str | None = None
    enrollment_type: str | None = None
    payment_method: str | None = None
    payment_status: str | None = None
    attendance_status: str | None = None
    incident_severity: str | None = None
    incident_status: str | None = None
    category_id: int | None = None
    summons_status: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "date_from": self.date_from.isoformat() if self.date_from else None,
            "date_to": self.date_to.isoformat() if self.date_to else None,
            "level": self.level_id,
            "section": self.section_id,
            "option": self.option_id,
            "class_id": self.class_id,
            "gender": self.gender,
            "fee_id": self.fee_id,
            "enrollment_status": self.enrollment_status,
            "enrollment_type": self.enrollment_type,
            "payment_method": self.payment_method,
            "payment_status": self.payment_status,
            "attendance_status": self.attendance_status,
            "incident_severity": self.incident_severity,
            "incident_status": self.incident_status,
            "category_id": self.category_id,
            "summons_status": self.summons_status,
        }


def parse_bi_filters(request: HttpRequest | None = None, **overrides) -> BiFilters:
    """Build BiFilters from GET params (and optional keyword overrides)."""
    get = getattr(request, "GET", {}) if request is not None else {}

    def g(*keys: str) -> str | None:
        for key in keys:
            value = get.get(key)
            if value not in (None, ""):
                return value
        return None

    gender = g("gender", "sexe")
    if gender:
        gender = gender.upper()

    data = {
        "date_from": _parse_date(g("date_from", "debut", "from")),
        "date_to": _parse_date(g("date_to", "fin", "to")),
        "level_id": _parse_int(g("level", "level_id")),
        "section_id": _parse_int(g("section", "section_id")),
        "option_id": _parse_int(g("option", "option_id")),
        "class_id": _parse_int(g("class_id", "classe", "school_class")),
        "gender": gender,
        "fee_id": _parse_int(g("fee_id", "fee")),
        "enrollment_status": g("enrollment_status", "status"),
        "enrollment_type": g("enrollment_type", "type"),
        "payment_method": g("payment_method", "mode"),
        "payment_status": g("payment_status"),
        "attendance_status": g("attendance_status"),
        "incident_severity": g("severity", "incident_severity"),
        "incident_status": g("incident_status"),
        "category_id": _parse_int(g("category_id", "category")),
        "summons_status": g("summons_status"),
    }
    data.update({k: v for k, v in overrides.items() if v is not None})
    return BiFilters(**data)


def apply_class_structure_filters(
    qs: QuerySet,
    filters: BiFilters,
    *,
    class_prefix: str = "school_class",
) -> QuerySet:
    """Filter by level / section / option / class via a SchoolClass FK path."""
    if filters.class_id:
        qs = qs.filter(**{f"{class_prefix}_id": filters.class_id})
    if filters.level_id:
        qs = qs.filter(**{f"{class_prefix}__level_id": filters.level_id})
    if filters.section_id:
        qs = qs.filter(**{f"{class_prefix}__section_id": filters.section_id})
    if filters.option_id:
        qs = qs.filter(**{f"{class_prefix}__option_id": filters.option_id})
    return qs


def apply_date_range(
    qs: QuerySet,
    filters: BiFilters,
    *,
    field: str,
) -> QuerySet:
    if filters.date_from:
        qs = qs.filter(**{f"{field}__gte": filters.date_from})
    if filters.date_to:
        qs = qs.filter(**{f"{field}__lte": filters.date_to})
    return qs
