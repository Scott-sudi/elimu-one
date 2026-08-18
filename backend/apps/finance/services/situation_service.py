"""Finance situation matrices, student balances, arrears and dashboard stats."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Count, DecimalField, F, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce

from apps.finance.models import Payment, SchoolFee, StudentFeeObligation
from apps.secretariat.models import AcademicYear, Enrollment, SchoolClass, Student


ZERO = Decimal("0.00")
MONEY = DecimalField(max_digits=14, decimal_places=2)


def arrears_queryset(
    *,
    academic_year: AcademicYear | None = None,
    school_class: SchoolClass | None = None,
) -> QuerySet[StudentFeeObligation]:
    """Obligations still owing money (unpaid or partial), excluding exempted/cancelled."""
    qs = (
        StudentFeeObligation.objects.filter(
            status__in=[
                StudentFeeObligation.Status.UNPAID,
                StudentFeeObligation.Status.PARTIAL,
            ],
            amount_paid__lt=F("amount_due"),
        )
        .select_related(
            "fee",
            "fee__category",
            "enrollment",
            "enrollment__school_class",
            "student",
        )
        .order_by(
            "enrollment__school_class__name",
            "student__nom",
            "student__postnom",
            "student__prenom",
            "fee__label",
        )
    )
    if academic_year is not None:
        qs = qs.filter(fee__academic_year=academic_year)
    if school_class is not None:
        qs = qs.filter(enrollment__school_class=school_class)
    return qs


def student_situation(
    *,
    enrollment: Enrollment | None = None,
    student: Student | None = None,
    academic_year: AcademicYear | None = None,
) -> dict[str, Any]:
    """Return obligation/payment summary for one enrollment or student+year."""
    if enrollment is None:
        if student is None or academic_year is None:
            raise ValueError(
                "Provide either enrollment, or student with academic_year."
            )
        enrollment = (
            Enrollment.objects.select_related("student", "school_class", "academic_year")
            .filter(
                student=student,
                academic_year=academic_year,
                status=Enrollment.Status.VALIDATED,
            )
            .order_by("-enrollment_date", "-created_at")
            .first()
        )
        if enrollment is None:
            return {
                "enrollment": None,
                "obligations": [],
                "totals": {
                    "amount_due": ZERO,
                    "amount_paid": ZERO,
                    "amount_remaining": ZERO,
                    "tone": "paid",
                },
                "payments": [],
            }
    else:
        enrollment = Enrollment.objects.select_related(
            "student",
            "school_class",
            "academic_year",
        ).get(pk=enrollment.pk)

    obligations = list(
        StudentFeeObligation.objects.filter(enrollment=enrollment)
        .exclude(status=StudentFeeObligation.Status.CANCELLED)
        .select_related("fee", "fee__category")
        .order_by("fee__label")
    )
    amount_due = sum((o.amount_due for o in obligations), ZERO)
    amount_paid = sum((o.amount_paid for o in obligations), ZERO)
    amount_remaining = sum((o.amount_remaining for o in obligations), ZERO)

    if amount_paid <= ZERO and amount_remaining > ZERO:
        totals_tone = "unpaid"
    elif amount_remaining <= ZERO:
        totals_tone = "paid"
    else:
        totals_tone = "partial"

    payments = list(
        Payment.objects.filter(enrollment=enrollment)
        .prefetch_related("allocations__obligation__fee")
        .order_by("-payment_date", "-created_at")
    )

    return {
        "enrollment": enrollment,
        "student": enrollment.student,
        "school_class": enrollment.school_class,
        "academic_year": enrollment.academic_year,
        "obligations": [
            {
                "obligation": o,
                "fee": o.fee,
                "amount_due": o.amount_due,
                "amount_paid": o.amount_paid,
                "amount_remaining": o.amount_remaining,
                "status": o.status,
                "tone": o.payment_tone,
            }
            for o in obligations
        ],
        "totals": {
            "amount_due": amount_due,
            "amount_paid": amount_paid,
            "amount_remaining": amount_remaining,
            "tone": totals_tone,
        },
        "payments": payments,
    }


def class_situation_matrix(
    *,
    school_class: SchoolClass,
    include_cancelled: bool = False,
    board: str | None = None,
    fees: list[SchoolFee] | None = None,
) -> dict[str, Any]:
    """Build a student × fee matrix of remaining balances for a class."""
    enrollments = list(
        Enrollment.objects.filter(
            school_class=school_class,
            status=Enrollment.Status.VALIDATED,
        )
        .select_related("student")
        .order_by("student__nom", "student__postnom", "student__prenom")
    )
    enrollment_ids = [e.pk for e in enrollments]

    if fees is None:
        fee_qs = SchoolFee.objects.filter(
            academic_year_id=school_class.academic_year_id,
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
        ).select_related("category")
        if board:
            from apps.finance.services.fee_structure_service import (
                CATEGORY_CODES_BY_BOARD,
                BOARD_ETAT,
                BOARD_MINERVAL,
            )

            codes = CATEGORY_CODES_BY_BOARD.get(board, ())
            fee_qs = fee_qs.filter(category__code__in=codes)
            if board == BOARD_MINERVAL:
                fees = list(fee_qs.order_by("due_date", "code", "label"))
            elif board == BOARD_ETAT:
                fees = list(fee_qs.order_by("code", "label"))
            else:
                fees = list(fee_qs.order_by("category__order", "label", "code"))
        else:
            # Legacy: only fees that already have obligations in the class
            fees = list(
                fee_qs.filter(obligations__enrollment_id__in=enrollment_ids)
                .distinct()
                .order_by("category__order", "label")
            )
    else:
        fees = list(fees)

    obligation_qs = StudentFeeObligation.objects.filter(
        enrollment_id__in=enrollment_ids,
        fee_id__in=[f.pk for f in fees],
    )
    if not include_cancelled:
        obligation_qs = obligation_qs.exclude(
            status=StudentFeeObligation.Status.CANCELLED
        )

    by_key: dict[tuple[int, int], StudentFeeObligation] = {
        (o.enrollment_id, o.fee_id): o for o in obligation_qs
    }

    rows: list[dict[str, Any]] = []
    for enrollment in enrollments:
        cells = []
        row_due = ZERO
        row_paid = ZERO
        row_remaining = ZERO
        for fee in fees:
            obligation = by_key.get((enrollment.pk, fee.pk))
            if obligation is None:
                cells.append(
                    {
                        "fee": fee,
                        "obligation": None,
                        "amount_due": None,
                        "amount_paid": None,
                        "amount_remaining": None,
                        "status": None,
                    }
                )
                continue
            cells.append(
                {
                    "fee": fee,
                    "obligation": obligation,
                    "amount_due": obligation.amount_due,
                    "amount_paid": obligation.amount_paid,
                    "amount_remaining": obligation.amount_remaining,
                    "status": obligation.status,
                }
            )
            row_due += obligation.amount_due
            row_paid += obligation.amount_paid
            row_remaining += obligation.amount_remaining

        if row_due <= ZERO or row_paid <= ZERO:
            row_tone = "unpaid"  # rien payé → rouge
        elif row_remaining <= ZERO:
            row_tone = "paid"  # soldé → vert
        else:
            row_tone = "partial"  # avance → orange

        rows.append(
            {
                "enrollment": enrollment,
                "student": enrollment.student,
                "cells": cells,
                "row_tone": row_tone,
                "totals": {
                    "amount_due": row_due,
                    "amount_paid": row_paid,
                    "amount_remaining": row_remaining,
                },
            }
        )

    column_totals = []
    for fee in fees:
        due = ZERO
        paid = ZERO
        remaining = ZERO
        for row in rows:
            for cell in row["cells"]:
                if cell["fee"].pk != fee.pk or cell["obligation"] is None:
                    continue
                due += cell["amount_due"]
                paid += cell["amount_paid"]
                remaining += cell["amount_remaining"]
        column_totals.append(
            {
                "fee": fee,
                "amount_due": due,
                "amount_paid": paid,
                "amount_remaining": remaining,
            }
        )

    return {
        "school_class": school_class,
        "academic_year": school_class.academic_year,
        "fees": fees,
        "rows": rows,
        "column_totals": column_totals,
        "grand_totals": {
            "amount_due": sum((c["amount_due"] for c in column_totals), ZERO),
            "amount_paid": sum((c["amount_paid"] for c in column_totals), ZERO),
            "amount_remaining": sum(
                (c["amount_remaining"] for c in column_totals), ZERO
            ),
        },
    }


def dashboard_stats(*, academic_year: AcademicYear) -> dict[str, Any]:
    """Aggregate finance KPIs for the selected academic year."""
    obligation_agg = StudentFeeObligation.objects.filter(
        fee__academic_year=academic_year,
    ).exclude(
        status=StudentFeeObligation.Status.CANCELLED,
    ).aggregate(
        total_due=Coalesce(Sum("amount_due"), Value(ZERO), output_field=MONEY),
        total_paid=Coalesce(Sum("amount_paid"), Value(ZERO), output_field=MONEY),
        obligation_count=Count("id"),
        unpaid_count=Count(
            "id",
            filter=Q(status=StudentFeeObligation.Status.UNPAID),
        ),
        partial_count=Count(
            "id",
            filter=Q(status=StudentFeeObligation.Status.PARTIAL),
        ),
        paid_count=Count(
            "id",
            filter=Q(status=StudentFeeObligation.Status.PAID),
        ),
        exempted_count=Count(
            "id",
            filter=Q(status=StudentFeeObligation.Status.EXEMPTED),
        ),
    )

    total_due = Decimal(obligation_agg["total_due"] or ZERO)
    total_paid = Decimal(obligation_agg["total_paid"] or ZERO)
    total_remaining = total_due - total_paid
    if total_remaining < 0:
        total_remaining = ZERO

    payments_agg = Payment.objects.filter(
        academic_year=academic_year,
        status=Payment.Status.VALID,
    ).aggregate(
        payment_count=Count("id"),
        payments_total=Coalesce(Sum("amount_total"), Value(ZERO), output_field=MONEY),
    )

    fees_agg = SchoolFee.objects.filter(academic_year=academic_year).aggregate(
        draft_count=Count("id", filter=Q(status=SchoolFee.Status.DRAFT)),
        pending_count=Count("id", filter=Q(status=SchoolFee.Status.PENDING)),
        approved_count=Count("id", filter=Q(status=SchoolFee.Status.APPROVED)),
        rejected_count=Count("id", filter=Q(status=SchoolFee.Status.REJECTED)),
    )

    arrears = arrears_queryset(academic_year=academic_year)
    arrears_total = arrears.aggregate(
        total=Coalesce(
            Sum(F("amount_due") - F("amount_paid")),
            Value(ZERO),
            output_field=MONEY,
        )
    )["total"]

    return {
        "academic_year": academic_year,
        "totals": {
            "amount_due": total_due,
            "amount_paid": total_paid,
            "amount_remaining": total_remaining,
            "arrears_total": Decimal(arrears_total or ZERO),
        },
        "obligations": {
            "count": obligation_agg["obligation_count"],
            "unpaid": obligation_agg["unpaid_count"],
            "partial": obligation_agg["partial_count"],
            "paid": obligation_agg["paid_count"],
            "exempted": obligation_agg["exempted_count"],
        },
        "payments": {
            "count": payments_agg["payment_count"],
            "total": Decimal(payments_agg["payments_total"] or ZERO),
        },
        "fees": fees_agg,
        "arrears_count": arrears.count(),
    }
