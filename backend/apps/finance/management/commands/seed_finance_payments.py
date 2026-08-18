"""Seed unbalanced finance payments for the open academic year (demo data).

Pays existing structural fees only (minerval + frais d'État). Minerval payments
stop at March — April, May, June (and July) stay unpaid. Profiles vary by class
so totals are intentionally uneven.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.finance.models import Payment, SchoolFee, StudentFeeObligation
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.fee_structure_service import ensure_structural_fees
from apps.finance.services.obligation_service import recalculate_obligation
from apps.finance.services.payment_service import cancel_payment, record_payment
from apps.secretariat.models import AcademicYear, Enrollment, SchoolClass


# Minerval months we may pay (Sept → March). Later months stay unpaid.
PAYABLE_MINERVAL_CODES_SUFFIX = (
    "09",  # Sept
    "10",  # Oct
    "11",  # Nov
    "12",  # Dec
    "01",  # Jan
    "02",  # Feb
    "03",  # Mar
)

METHODS = (
    Payment.PaymentMethod.CASH,
    Payment.PaymentMethod.CASH,
    Payment.PaymentMethod.CASH,
    Payment.PaymentMethod.MOBILE_MONEY,
    Payment.PaymentMethod.MOBILE_MONEY,
    Payment.PaymentMethod.TRANSFER,
)


def _stable_rng(*parts: str) -> random.Random:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _pick_actor() -> User | None:
    return (
        User.objects.filter(role__code=Role.CODE_COMPTABLE, is_active=True)
        .order_by("id")
        .first()
        or User.objects.filter(is_active=True).order_by("id").first()
    )


def _open_year() -> AcademicYear:
    year = (
        AcademicYear.objects.filter(is_closed=False)
        .order_by("-start_date")
        .first()
    )
    if year is None:
        raise CommandError("Aucune année scolaire ouverte.")
    return year


def _minerval_fees_through_march(year: AcademicYear) -> list[SchoolFee]:
    fees = list(
        SchoolFee.objects.filter(
            academic_year=year,
            category__code="MINERVAL",
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
        ).order_by("code")
    )
    payable = []
    for fee in fees:
        # codes like MIN-202509 … MIN-202603
        suffix = fee.code[-2:] if fee.code else ""
        month = int(suffix) if suffix.isdigit() else 0
        # Include Sept–Dec of start year and Jan–Mar of next year
        if month in {9, 10, 11, 12, 1, 2, 3}:
            # Exclude Apr–Jul which also end with those? Apr=04 — not in set. Good.
            # But Jan=01 is in set — only keep if fee is before April of end year.
            if fee.due_date and fee.due_date.month in {4, 5, 6, 7}:
                continue
            payable.append(fee)
    # Sort chronologically by due_date/code
    payable.sort(key=lambda f: (f.due_date or date.min, f.code))
    # Keep only through March: stop when we hit first month > 3 after year turn
    result = []
    for fee in payable:
        result.append(fee)
        if fee.due_date and fee.due_date.month == 3:
            break
    return result


def _etat_fees(year: AcademicYear) -> list[SchoolFee]:
    return list(
        SchoolFee.objects.filter(
            academic_year=year,
            category__code="FRAIS_ETAT",
            status=SchoolFee.Status.APPROVED,
            is_active=True,
            is_archived=False,
        ).order_by("code")
    )


def _class_bias(school_class: SchoolClass) -> str:
    """Give each class a dominant payment mood for imbalance across classes."""
    moods = (
        "strong",  # mostly up to date through March
        "strong",
        "mixed",
        "mixed",
        "lagging",  # mostly behind
        "poor",  # many unpaid
        "mixed",
    )
    rng = _stable_rng("class-bias", str(school_class.public_id))
    return rng.choice(moods)


def _student_profile(enrollment: Enrollment, class_mood: str) -> str:
    rng = _stable_rng("student", str(enrollment.public_id), class_mood)
    weights = {
        "strong": [
            ("full_march", 45),
            ("partial_march", 20),
            ("through_feb", 15),
            ("mid_year_stop", 10),
            ("early_only", 5),
            ("nothing", 5),
        ],
        "mixed": [
            ("full_march", 18),
            ("partial_march", 22),
            ("through_feb", 18),
            ("mid_year_stop", 18),
            ("early_only", 14),
            ("nothing", 10),
        ],
        "lagging": [
            ("full_march", 8),
            ("partial_march", 12),
            ("through_feb", 15),
            ("mid_year_stop", 25),
            ("early_only", 25),
            ("nothing", 15),
        ],
        "poor": [
            ("full_march", 3),
            ("partial_march", 7),
            ("through_feb", 10),
            ("mid_year_stop", 20),
            ("early_only", 30),
            ("nothing", 30),
        ],
    }[class_mood]
    population, w = zip(*weights)
    return rng.choices(population, weights=w, k=1)[0]


def _months_for_profile(profile: str, minerval_fees: list[SchoolFee]) -> tuple[list[SchoolFee], Decimal | None]:
    """
    Return (full months to pay, optional partial amount on next month).
    Partial applies to the month after the last full one (usually March).
    """
    n = len(minerval_fees)
    if n == 0:
        return [], None

    if profile == "nothing":
        return [], None
    if profile == "early_only":
        # Sept–Oct or Sept only
        count = 1 if n == 1 else 2
        return minerval_fees[:count], None
    if profile == "mid_year_stop":
        # through Nov or Dec
        count = min(n, 3 if n >= 3 else n)
        return minerval_fees[:count], None
    if profile == "through_feb":
        # all except March (last)
        if n <= 1:
            return minerval_fees[:1], None
        return minerval_fees[:-1], None
    if profile == "partial_march":
        full = minerval_fees[:-1] if n > 1 else []
        # partial on March (or only month)
        partial_fee = minerval_fees[-1]
        due = partial_fee.amount
        # uneven partials: 10k, 15k, 20k, 25k, 30k, 35k…
        options = [
            Decimal("10000.00"),
            Decimal("15000.00"),
            Decimal("20000.00"),
            Decimal("25000.00"),
            Decimal("30000.00"),
            Decimal("35000.00"),
            Decimal("40000.00"),
        ]
        amount = max((a for a in options if a < due), default=Decimal("10000.00"))
        return full, amount
    # full_march
    return minerval_fees, None


def _etat_plan(profile: str, etat_fees: list[SchoolFee], rng: random.Random) -> list[tuple[SchoolFee, Decimal]]:
    if not etat_fees:
        return []
    t1 = etat_fees[0]
    t2 = etat_fees[1] if len(etat_fees) > 1 else None
    t3 = etat_fees[2] if len(etat_fees) > 2 else None
    plan: list[tuple[SchoolFee, Decimal]] = []

    if profile == "nothing":
        return []
    if profile in {"early_only", "mid_year_stop"}:
        if rng.random() < 0.55:
            plan.append((t1, t1.amount))
        elif rng.random() < 0.5:
            partial = Decimal(rng.choice(["5000.00", "10000.00", "15000.00"]))
            plan.append((t1, min(partial, t1.amount)))
        return plan
    if profile == "through_feb":
        plan.append((t1, t1.amount))
        if t2 and rng.random() < 0.4:
            plan.append((t2, t2.amount))
        return plan
    if profile == "partial_march":
        plan.append((t1, t1.amount))
        if t2:
            if rng.random() < 0.55:
                plan.append((t2, t2.amount))
            else:
                partial = Decimal(rng.choice(["8000.00", "12000.00", "18000.00"]))
                plan.append((t2, min(partial, t2.amount)))
        return plan
    # full_march — often T1+T2, rarely T3 (still "before April" story)
    plan.append((t1, t1.amount))
    if t2 and rng.random() < 0.75:
        plan.append((t2, t2.amount))
    if t3 and rng.random() < 0.12:
        plan.append((t3, t3.amount))
    return plan


def _payment_date_for_fee(fee: SchoolFee, rng: random.Random) -> date:
    if fee.due_date:
        base = fee.due_date.replace(day=1)
        day = rng.randint(1, 20)
        try:
            return base.replace(day=day)
        except ValueError:
            return base
    return timezone.localdate() - timedelta(days=rng.randint(10, 120))


def _obligation_map(enrollment: Enrollment) -> dict[int, StudentFeeObligation]:
    obs = StudentFeeObligation.objects.filter(enrollment=enrollment).select_related("fee")
    return {o.fee_id: o for o in obs}


class Command(BaseCommand):
    help = (
        "Génère des paiements déséquilibrés (reçus inclus) sur l'année ouverte, "
        "en s'arrêtant au minerval de mars. N'ajoute aucun nouveau frais."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Annule les paiements existants de l'année ouverte avant de régénérer.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limiter au N premiers élèves (0 = tous).",
        )

    def handle(self, *args, **options):
        year = _open_year()
        actor = _pick_actor()
        self.stdout.write(f"Année : {year.label}")
        ensure_structural_fees(academic_year=year, actor=actor)

        minerval_fees = _minerval_fees_through_march(year)
        etat_fees = _etat_fees(year)
        if not minerval_fees:
            raise CommandError("Aucun frais minerval trouvé jusqu'à mars.")
        self.stdout.write(
            "Minerval payables : "
            + ", ".join(f.label for f in minerval_fees)
        )

        if options["reset"]:
            self._reset_payments(year, actor)

        enrollments = list(
            Enrollment.objects.filter(
                academic_year=year,
                status=Enrollment.Status.VALIDATED,
            )
            .select_related("student", "school_class")
            .order_by("school_class__name", "student__nom", "student__prenom")
        )
        if options["limit"]:
            enrollments = enrollments[: options["limit"]]

        created = 0
        skipped = 0
        errors = 0

        for enrollment in enrollments:
            # Skip students who already have valid payments unless we just reset
            if (
                not options["reset"]
                and Payment.objects.filter(
                    enrollment=enrollment, status=Payment.Status.VALID
                ).exists()
            ):
                skipped += 1
                continue

            mood = _class_bias(enrollment.school_class)
            profile = _student_profile(enrollment, mood)
            rng = _stable_rng("pay", str(enrollment.public_id), profile)
            full_months, march_partial = _months_for_profile(profile, minerval_fees)
            etat_plan = _etat_plan(profile, etat_fees, rng)
            obligations = _obligation_map(enrollment)

            try:
                n = self._seed_enrollment(
                    enrollment=enrollment,
                    obligations=obligations,
                    full_months=full_months,
                    march_partial_fee=minerval_fees[-1] if march_partial else None,
                    march_partial_amount=march_partial,
                    etat_plan=etat_plan,
                    rng=rng,
                    actor=actor,
                )
                created += n
            except Exception as exc:  # noqa: BLE001 — keep seeding others
                errors += 1
                self.stderr.write(
                    f"Erreur {enrollment.student.matricule}: {exc}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Terminé — {created} paiement(s), {skipped} élève(s) ignoré(s), "
                f"{errors} erreur(s)."
            )
        )

    def _reset_payments(self, year: AcademicYear, actor: User | None) -> None:
        qs = Payment.objects.filter(academic_year=year, status=Payment.Status.VALID)
        count = qs.count()
        self.stdout.write(f"Annulation de {count} paiement(s) existant(s)…")
        for payment in qs.iterator():
            try:
                cancel_payment(
                    payment=payment,
                    reason="Reset seed_finance_payments",
                    actor=actor,
                )
            except FinanceError:
                # Fallback hard reset for demo
                obligation_ids = list(
                    payment.allocations.values_list("obligation_id", flat=True)
                )
                payment.allocations.all().delete()
                payment.status = Payment.Status.CANCELLED
                payment.cancellation_reason = "Reset seed_finance_payments"
                payment.save(update_fields=["status", "cancellation_reason", "updated_at"])
                for oid in obligation_ids:
                    try:
                        recalculate_obligation(
                            StudentFeeObligation.objects.get(pk=oid)
                        )
                    except StudentFeeObligation.DoesNotExist:
                        pass

    @transaction.atomic
    def _seed_enrollment(
        self,
        *,
        enrollment: Enrollment,
        obligations: dict[int, StudentFeeObligation],
        full_months: list[SchoolFee],
        march_partial_fee: SchoolFee | None,
        march_partial_amount: Decimal | None,
        etat_plan: list[tuple[SchoolFee, Decimal]],
        rng: random.Random,
        actor: User | None,
    ) -> int:
        created = 0

        def pay(fee: SchoolFee, amount: Decimal, when: date) -> None:
            nonlocal created
            obligation = obligations.get(fee.pk)
            if obligation is None:
                return
            obligation.refresh_from_db()
            remaining = obligation.amount_remaining
            if remaining <= 0:
                return
            amount = min(amount, remaining).quantize(Decimal("0.01"))
            if amount <= 0:
                return
            record_payment(
                enrollment=enrollment,
                amount_total=amount,
                allocations=[{"obligation": obligation, "amount": amount}],
                payment_date=when,
                currency=fee.currency or "CDF",
                payment_method=rng.choice(METHODS),
                observation="Données de démonstration",
                actor=actor,
            )
            created += 1

        # Sometimes combine 2 consecutive full months in one receipt for variety
        i = 0
        while i < len(full_months):
            fee = full_months[i]
            if (
                i + 1 < len(full_months)
                and rng.random() < 0.22
            ):
                fee_b = full_months[i + 1]
                ob_a = obligations.get(fee.pk)
                ob_b = obligations.get(fee_b.pk)
                if ob_a and ob_b:
                    ob_a.refresh_from_db()
                    ob_b.refresh_from_db()
                    a1 = min(fee.amount, ob_a.amount_remaining)
                    a2 = min(fee_b.amount, ob_b.amount_remaining)
                    if a1 > 0 and a2 > 0:
                        total = (a1 + a2).quantize(Decimal("0.01"))
                        record_payment(
                            enrollment=enrollment,
                            amount_total=total,
                            allocations=[
                                {"obligation": ob_a, "amount": a1},
                                {"obligation": ob_b, "amount": a2},
                            ],
                            payment_date=_payment_date_for_fee(fee_b, rng),
                            currency=fee.currency or "CDF",
                            payment_method=rng.choice(METHODS),
                            observation="Données de démonstration (2 mois)",
                            actor=actor,
                        )
                        created += 1
                        i += 2
                        continue
            pay(fee, fee.amount, _payment_date_for_fee(fee, rng))
            i += 1

        if march_partial_fee and march_partial_amount:
            pay(
                march_partial_fee,
                march_partial_amount,
                _payment_date_for_fee(march_partial_fee, rng),
            )

        for fee, amount in etat_plan:
            pay(fee, amount, _payment_date_for_fee(fee, rng))

        return created
