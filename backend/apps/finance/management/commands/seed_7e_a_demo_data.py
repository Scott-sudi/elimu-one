"""Seed finance + attendance for the two known 7e A students only.

Matricules: KAL-2026-00001 (Scott), KAL-2026-00002 (Daniella).
Does NOT create students/guardians — only payments and daily attendance.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.discipline.models import DailyAttendance
from apps.discipline.services.attendance_service import register_manual_attendance
from apps.discipline.services.exceptions import DisciplineError
from apps.finance.models import Payment, SchoolFee, StudentFeeObligation
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.fee_structure_service import ensure_structural_fees
from apps.finance.services.obligation_service import (
    create_obligations_for_enrollment,
    recalculate_obligation,
)
from apps.finance.services.payment_service import cancel_payment, record_payment
from apps.secretariat.models import AcademicYear, Enrollment, Student

TARGET_MATRICULES = ("KAL-2026-00001", "KAL-2026-00002")

# Explicit unbalanced profiles (months = minerval count to pay fully).
PROFILES = {
    # Scott — plutôt à jour (5 mois minerval + 1er frais d'État)
    "KAL-2026-00001": {
        "minerval_months": 5,
        "etat_tranches": 1,
        "label": "5 mois minerval + T1 État",
    },
    # Daniella — en retard (3 mois minerval seulement, État impayé)
    "KAL-2026-00002": {
        "minerval_months": 3,
        "etat_tranches": 0,
        "label": "3 mois minerval, État impayé",
    },
}


def _pick_actor() -> User | None:
    return (
        User.objects.filter(role__code=Role.CODE_COMPTABLE, is_active=True)
        .order_by("id")
        .first()
        or User.objects.filter(is_active=True).order_by("id").first()
    )


def _resolve_year() -> AcademicYear:
    year = (
        AcademicYear.objects.filter(is_closed=False, is_active=True)
        .order_by("-start_date")
        .first()
        or AcademicYear.objects.filter(is_closed=False)
        .order_by("-start_date")
        .first()
    )
    if year is None:
        raise CommandError("Aucune année scolaire ouverte.")
    return year


def _minerval_ordered(year: AcademicYear) -> list[SchoolFee]:
    fees = list(
        SchoolFee.objects.filter(
            academic_year=year,
            category__code="MINERVAL",
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
        ).order_by("due_date", "code")
    )
    # Garder Sept→Mars (jusqu'au premier mois 3 inclus), comme seed_finance_payments.
    result: list[SchoolFee] = []
    for fee in fees:
        if fee.due_date and fee.due_date.month in {4, 5, 6, 7}:
            continue
        result.append(fee)
        if fee.due_date and fee.due_date.month == 3:
            break
    return result or fees


def _etat_ordered(year: AcademicYear) -> list[SchoolFee]:
    return list(
        SchoolFee.objects.filter(
            academic_year=year,
            category__code="FRAIS_ETAT",
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
        ).order_by("code")
    )


def _reset_enrollment_payments(enrollment: Enrollment, actor: User | None) -> int:
    qs = Payment.objects.filter(
        enrollment=enrollment,
        status=Payment.Status.VALID,
    )
    n = 0
    for payment in qs:
        try:
            cancel_payment(
                payment=payment,
                reason="Reset seed_7e_a_demo_data",
                actor=actor,
            )
            n += 1
        except FinanceError:
            obligation_ids = list(
                payment.allocations.values_list("obligation_id", flat=True)
            )
            payment.allocations.all().delete()
            payment.status = Payment.Status.CANCELLED
            payment.cancellation_reason = "Reset seed_7e_a_demo_data"
            payment.save(
                update_fields=["status", "cancellation_reason", "updated_at"]
            )
            for oid in obligation_ids:
                try:
                    recalculate_obligation(StudentFeeObligation.objects.get(pk=oid))
                except StudentFeeObligation.DoesNotExist:
                    pass
            n += 1
    return n


class Command(BaseCommand):
    help = (
        "Données démo 7e A : paiements déséquilibrés + présences/absences "
        "pour KAL-2026-00001 et KAL-2026-00002 uniquement."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-payments",
            action="store_true",
            help="Annule les paiements VALIDES existants de ces 2 élèves avant de régénérer.",
        )

    def handle(self, *args, **options):
        year = _resolve_year()
        actor = _pick_actor()
        self.stdout.write(f"Année : {year.label} (id={year.pk})")
        ensure_structural_fees(academic_year=year, actor=actor)

        minerval = _minerval_ordered(year)
        etat = _etat_ordered(year)
        if not minerval:
            raise CommandError("Aucun frais minerval APPROUVE.")
        self.stdout.write(
            "Minerval : " + ", ".join(f"{f.code}({f.label})" for f in minerval)
        )

        students = list(
            Student.objects.filter(matricule__in=TARGET_MATRICULES, is_archived=False)
        )
        found = {s.matricule: s for s in students}
        missing = [m for m in TARGET_MATRICULES if m not in found]
        if missing:
            raise CommandError(f"Matricules introuvables : {', '.join(missing)}")

        payments_created = 0
        attendance_created = 0

        for matricule in TARGET_MATRICULES:
            student = found[matricule]
            enrollment = (
                Enrollment.objects.filter(
                    student=student,
                    academic_year=year,
                    status=Enrollment.Status.VALIDATED,
                )
                .select_related("school_class")
                .first()
            )
            if enrollment is None:
                raise CommandError(
                    f"{matricule} : pas d'inscription VALIDEE pour {year.label}."
                )
            self.stdout.write(
                f"→ {matricule} | {enrollment.school_class.name} | "
                f"{PROFILES[matricule]['label']}"
            )

            create_obligations_for_enrollment(enrollment=enrollment)
            if options["reset_payments"]:
                cancelled = _reset_enrollment_payments(enrollment, actor)
                self.stdout.write(f"  paiements annulés : {cancelled}")

            payments_created += self._seed_finance(
                enrollment=enrollment,
                minerval=minerval,
                etat=etat,
                profile=PROFILES[matricule],
                actor=actor,
            )
            attendance_created += self._seed_attendance(
                year=year,
                enrollment=enrollment,
                actor=actor,
                seed=matricule,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"OK — {payments_created} paiement(s), "
                f"{attendance_created} jour(s) de présence/absence."
            )
        )

    @transaction.atomic
    def _seed_finance(
        self,
        *,
        enrollment: Enrollment,
        minerval: list[SchoolFee],
        etat: list[SchoolFee],
        profile: dict,
        actor: User | None,
    ) -> int:
        obligations = {
            o.fee_id: o
            for o in StudentFeeObligation.objects.filter(enrollment=enrollment)
        }
        created = 0
        n_months = min(int(profile["minerval_months"]), len(minerval))
        for fee in minerval[:n_months]:
            created += self._pay_fee(
                enrollment=enrollment,
                obligations=obligations,
                fee=fee,
                amount=fee.amount,
                actor=actor,
            )

        n_etat = min(int(profile["etat_tranches"]), len(etat))
        for fee in etat[:n_etat]:
            created += self._pay_fee(
                enrollment=enrollment,
                obligations=obligations,
                fee=fee,
                amount=fee.amount,
                actor=actor,
            )
        return created

    def _pay_fee(
        self,
        *,
        enrollment: Enrollment,
        obligations: dict[int, StudentFeeObligation],
        fee: SchoolFee,
        amount: Decimal,
        actor: User | None,
    ) -> int:
        obligation = obligations.get(fee.pk)
        if obligation is None:
            return 0
        obligation.refresh_from_db()
        remaining = obligation.amount_remaining
        if remaining <= 0:
            return 0
        amount = min(Decimal(amount), remaining).quantize(Decimal("0.01"))
        if amount <= 0:
            return 0
        when = fee.due_date.replace(day=min(12, fee.due_date.day)) if fee.due_date else timezone.localdate()
        record_payment(
            enrollment=enrollment,
            amount_total=amount,
            allocations=[{"obligation": obligation, "amount": amount}],
            payment_date=when,
            currency=fee.currency or "CDF",
            payment_method=Payment.PaymentMethod.CASH,
            observation="",
            actor=actor,
        )
        return 1

    def _seed_attendance(self, *, year, enrollment, actor, seed):
        """~12 jours ouvrés dans l'année scolaire (pas avant start_date)."""
        today = timezone.localdate()
        if seed.endswith("00001"):
            pattern = [
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.ABSENT,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.ABSENT,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.LATE,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.PRESENT,
            ]
        else:
            pattern = [
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.ABSENT,
                DailyAttendance.Status.ABSENT,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.ABSENT,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.ABSENT,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.ABSENT,
                DailyAttendance.Status.PRESENT,
                DailyAttendance.Status.ABSENT,
            ]

        start = year.start_date or today
        end = year.end_date or (today + timedelta(days=180))
        # Si on est avant le début d'année (ex. août pour une rentrée sept.),
        # on part du début d'année. Sinon on remonte depuis aujourd'hui.
        days: list[date] = []
        if today < start:
            cursor = start
            while len(days) < len(pattern) and cursor <= end:
                if cursor.weekday() < 5:
                    days.append(cursor)
                cursor += timedelta(days=1)
        else:
            cursor = min(today, end)
            while len(days) < len(pattern) and cursor >= start:
                if cursor.weekday() < 5:
                    days.append(cursor)
                cursor -= timedelta(days=1)
            days.reverse()

        created = 0
        for i, day in enumerate(days):
            status = pattern[i]
            try:
                with transaction.atomic():
                    register_manual_attendance(
                        academic_year=year,
                        enrollment=enrollment,
                        status=status,
                        actor=actor,
                        note="",
                        for_date=day,
                    )
                created += 1
            except DisciplineError as exc:
                self.stderr.write(f"  attendance skip {day}: {exc}")
        return created
