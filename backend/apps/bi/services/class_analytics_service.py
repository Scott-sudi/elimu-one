"""Class analytics for the Préfet BI module."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.bi.constants import (
    MONEY,
    OPEN_INCIDENT_STATUSES,
    PRESENT_LIKE,
    ZERO,
    occupancy_status,
)
from apps.bi.filters import BiFilters
from apps.bi.selectors.attendance_selectors import attendance_qs
from apps.bi.selectors.class_selectors import classes_analytics_qs
from apps.bi.selectors.discipline_selectors import incidents_qs
from apps.bi.selectors.financial_selectors import obligations_qs, valid_payments_qs
from apps.discipline.models import DailyAttendance
from apps.secretariat.models import AcademicYear


def build_class_analytics(
    academic_year: AcademicYear,
    filters: BiFilters | None = None,
) -> dict[str, Any]:
    filters = filters or BiFilters()
    classes = list(classes_analytics_qs(academic_year, filters))

    rows: list[dict[str, Any]] = []
    occupation_rates: list[float] = []
    status_counts = {
        "Faiblement occupée": 0,
        "Occupation normale": 0,
        "Presque complète": 0,
        "Complète": 0,
        "Capacité dépassée": 0,
        "Capacité indéfinie": 0,
    }

    for school_class in classes:
        capacity = school_class.max_capacity or 0
        occupied = school_class.occupied or 0
        rate = round(occupied * 100 / capacity, 1) if capacity else None
        if rate is not None:
            occupation_rates.append(rate)
        statut = occupancy_status(occupied=occupied, capacity=capacity)
        status_counts[statut] = status_counts.get(statut, 0) + 1

        class_filter = BiFilters(
            **{**filters.__dict__, "class_id": school_class.pk}
        )
        fin_ob = obligations_qs(academic_year, class_filter).aggregate(
            due=Coalesce(Sum("amount_due"), Value(ZERO), output_field=MONEY),
        )
        fin_pay = valid_payments_qs(academic_year, class_filter).aggregate(
            collected=Coalesce(Sum("amount_total"), Value(ZERO), output_field=MONEY),
        )
        attendu = Decimal(fin_ob["due"] or ZERO)
        encaisse = Decimal(fin_pay["collected"] or ZERO)
        recovery = None
        if attendu > ZERO:
            recovery = float(
                (encaisse * Decimal("100") / attendu).quantize(Decimal("0.1"))
            )

        att = attendance_qs(academic_year, class_filter).aggregate(
            total=Count("id"),
            present_like=Count("id", filter=Q(status__in=PRESENT_LIKE)),
            late=Count("id", filter=Q(status=DailyAttendance.Status.LATE)),
        )
        att_total = att["total"] or 0
        presence = (
            round(att["present_like"] * 100 / att_total, 1) if att_total else None
        )

        incidents_open = incidents_qs(academic_year, class_filter).filter(
            status__in=OPEN_INCIDENT_STATUSES
        ).count()

        rows.append(
            {
                "class_id": school_class.pk,
                "name": school_class.name,
                "level": school_class.level.name if school_class.level_id else "",
                "section": school_class.section.name if school_class.section_id else "",
                "option": school_class.option.name if school_class.option_id else "",
                "capacity": capacity,
                "effectif": occupied,
                "garcons": school_class.boys or 0,
                "filles": school_class.girls or 0,
                "places_restantes": max(capacity - occupied, 0) if capacity else None,
                "taux_occupation": rate,
                "statut": statut,
                "montant_attendu": attendu,
                "montant_encaisse": encaisse,
                "taux_recouvrement": recovery,
                "taux_presence": presence,
                "retards": att["late"] or 0,
                "incidents_ouverts": incidents_open,
            }
        )

    occupation_moyenne = (
        round(sum(occupation_rates) / len(occupation_rates), 1)
        if occupation_rates
        else None
    )

    return {
        "kpis": {
            "classes_actives": len(rows),
            "occupation_moyenne": occupation_moyenne,
            "faiblement_occupees": status_counts.get("Faiblement occupée", 0),
            "presque_completes": status_counts.get("Presque complète", 0),
            "completes": status_counts.get("Complète", 0),
            "capacite_depassee": status_counts.get("Capacité dépassée", 0),
        },
        "charts": {
            "occupation": {
                "labels": [r["name"] for r in rows],
                "series": [
                    {
                        "name": "Taux d'occupation (%)",
                        "data": [
                            r["taux_occupation"]
                            if r["taux_occupation"] is not None
                            else 0
                            for r in rows
                        ],
                    }
                ],
            },
            "comparison": {
                "labels": [r["name"] for r in rows],
                "series": [
                    {
                        "name": "Effectif",
                        "data": [r["effectif"] for r in rows],
                    },
                    {
                        "name": "Capacité",
                        "data": [r["capacity"] for r in rows],
                    },
                ],
            },
            "status": {
                "labels": list(status_counts.keys()),
                "series": [
                    {
                        "name": "Classes",
                        "data": list(status_counts.values()),
                    }
                ],
            },
        },
        "tables": {
            "classes": rows,
        },
        "filters": filters.as_dict(),
        "generated_at": timezone.now(),
    }
