"""Finance (comptabilité) module tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.services import create_initial_administrator, ensure_system_roles
from apps.finance.models import Payment, SchoolFee, StudentFeeObligation
from apps.finance.services.exceptions import FinanceError
from apps.finance.services.fee_approval_service import approve_fee, reject_fee
from apps.finance.services.fee_service import (
    create_draft_fee,
    ensure_default_fee_categories,
    submit_fee,
)
from apps.finance.services.payment_service import cancel_payment, record_payment
from apps.secretariat.models import Enrollment, Student
from apps.secretariat.services.academic_service import (
    create_academic_year,
    create_level,
    create_school_class,
    create_section,
)
from apps.secretariat.services.enrollment_service import create_enrollment
from apps.secretariat.services.student_service import create_student
from apps.secretariat.services.year_context import SESSION_KEY


@pytest.fixture
def roles(db):
    return ensure_system_roles()


@pytest.fixture
def admin_user(roles):
    return create_initial_administrator(
        nom="Mbala",
        postnom="Jean",
        prenom="Patrick",
        telephone="0990000000",
        email="admin@kalunga.local",
        username="admin.kalunga",
        password="AdminPass123!",
    )


@pytest.fixture
def secretary(roles):
    return User.objects.create_user(
        username="secretaire1",
        password="TempPass123!",
        nom="Nzuzi",
        prenom="Marie",
        role=roles[Role.CODE_SECRETAIRE],
    )


@pytest.fixture
def accountant(roles):
    return User.objects.create_user(
        username="comptable1",
        password="TempPass123!",
        nom="Kabasele",
        prenom="Paul",
        role=roles[Role.CODE_COMPTABLE],
    )


@pytest.fixture
def academic_structure(db):
    year = create_academic_year(
        label="2026-2027",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 7, 31),
        is_active=True,
    )
    level = create_level(name="Première secondaire", code="1SEC", order=10)
    section = create_section(name="Générale", code="GEN")
    school_class = create_school_class(
        academic_year=year,
        level=level,
        section=section,
        letter="A",
        name="1re A",
        code="1A-2026",
        max_capacity=40,
    )
    return {
        "year": year,
        "level": level,
        "section": section,
        "school_class": school_class,
    }


@pytest.fixture
def enrolled_student(academic_structure, secretary):
    student = create_student(
        nom="Ilunga",
        prenom="Grace",
        sexe=Student.Gender.FEMALE,
        date_naissance=date(2011, 3, 15),
        date_admission=date(2026, 9, 1),
    )
    enrollment = create_enrollment(
        student=student,
        school_class=academic_structure["school_class"],
        enrollment_type=Enrollment.EnrollmentType.NEW,
        actor=secretary,
        skip_reenrollment_guard=True,
    )
    return {"student": student, "enrollment": enrollment}


def _set_year(client, year):
    session = client.session
    session[SESSION_KEY] = year.pk
    session.save()


@pytest.mark.django_db
def test_accountant_redirected_to_finance_dashboard(client, accountant, academic_structure):
    client.force_login(accountant)
    _set_year(client, academic_structure["year"])
    response = client.get(reverse("dashboard:home"))
    assert response.status_code == 302
    assert response.url == reverse("finance:dashboard")


@pytest.mark.django_db
def test_fee_workflow_approve_creates_obligations(
    accountant, secretary, academic_structure, enrolled_student
):
    categories = ensure_default_fee_categories()
    year = academic_structure["year"]
    fee = create_draft_fee(
        academic_year=year,
        category=categories[0],
        code="SCOL1",
        label="Scolarité T1",
        amount=Decimal("100000.00"),
        actor=accountant,
    )
    submit_fee(fee=fee, actor=accountant)
    fee.refresh_from_db()
    assert fee.status == SchoolFee.Status.PENDING

    approve_fee(fee=fee, actor=secretary)
    fee.refresh_from_db()
    assert fee.status == SchoolFee.Status.APPROVED
    obligation = StudentFeeObligation.objects.get(
        fee=fee, enrollment=enrolled_student["enrollment"]
    )
    assert obligation.amount_due == Decimal("100000.00")
    assert obligation.status == StudentFeeObligation.Status.UNPAID


@pytest.mark.django_db
def test_reject_fee_requires_reason(accountant, secretary, academic_structure):
    categories = ensure_default_fee_categories()
    fee = create_draft_fee(
        academic_year=academic_structure["year"],
        category=categories[0],
        code="EXAM1",
        label="Examen",
        amount=Decimal("25000.00"),
        actor=accountant,
    )
    submit_fee(fee=fee, actor=accountant)
    with pytest.raises(FinanceError):
        reject_fee(fee=fee, reason="", actor=secretary)


@pytest.mark.django_db
def test_payment_allocation_and_cancel(
    accountant, secretary, academic_structure, enrolled_student
):
    categories = ensure_default_fee_categories()
    fee = create_draft_fee(
        academic_year=academic_structure["year"],
        category=categories[0],
        code="SCOL2",
        label="Scolarité T2",
        amount=Decimal("50000.00"),
        actor=accountant,
    )
    submit_fee(fee=fee, actor=accountant)
    approve_fee(fee=fee, actor=secretary)
    obligation = StudentFeeObligation.objects.get(fee=fee)

    payment = record_payment(
        enrollment=enrolled_student["enrollment"],
        amount_total=Decimal("20000.00"),
        payment_date=date(2026, 10, 1),
        payment_method=Payment.PaymentMethod.CASH,
        allocations=[{"obligation": obligation, "amount": Decimal("20000.00")}],
        actor=accountant,
    )
    obligation.refresh_from_db()
    assert payment.receipt_number.startswith("REC-")
    assert obligation.status == StudentFeeObligation.Status.PARTIAL
    assert obligation.amount_paid == Decimal("20000.00")

    cancel_payment(
        payment=payment,
        reason="Erreur de saisie",
        actor=accountant,
    )
    payment.refresh_from_db()
    obligation.refresh_from_db()
    assert payment.status == Payment.Status.CANCELLED
    assert obligation.amount_paid == Decimal("0.00")
    assert obligation.status == StudentFeeObligation.Status.UNPAID


@pytest.mark.django_db
def test_new_enrollment_gets_approved_fee_obligation(
    accountant, secretary, academic_structure
):
    categories = ensure_default_fee_categories()
    fee = create_draft_fee(
        academic_year=academic_structure["year"],
        category=categories[0],
        code="INSCR",
        label="Inscription",
        amount=Decimal("15000.00"),
        actor=accountant,
    )
    submit_fee(fee=fee, actor=accountant)
    approve_fee(fee=fee, actor=secretary)

    student = create_student(
        nom="Mwamba",
        prenom="Leo",
        sexe=Student.Gender.MALE,
        date_naissance=date(2010, 5, 1),
        date_admission=date(2026, 9, 5),
    )
    enrollment = create_enrollment(
        student=student,
        school_class=academic_structure["school_class"],
        enrollment_type=Enrollment.EnrollmentType.NEW,
        actor=secretary,
        skip_reenrollment_guard=True,
    )
    assert StudentFeeObligation.objects.filter(fee=fee, enrollment=enrollment).exists()


@pytest.mark.django_db
def test_finance_api_requires_accountant(accountant, secretary, academic_structure):
    api = APIClient()
    api.force_authenticate(user=secretary)
    denied = api.get("/api/v1/finance/dashboard/")
    assert denied.status_code in {403, 400}

    api.force_authenticate(user=accountant)
    session = api.session
    session[SESSION_KEY] = academic_structure["year"].pk
    session.save()
    ok = api.get("/api/v1/finance/dashboard/")
    assert ok.status_code == 200
    assert "totals" in ok.data
    assert "amount_due" in ok.data["totals"]


@pytest.mark.django_db
def test_class_minerval_board_has_monthly_columns(
    client, accountant, academic_structure, enrolled_student
):
    from apps.finance.services.fee_structure_service import (
        BOARD_MINERVAL,
        ensure_structural_fees,
        iter_academic_months,
    )

    year = academic_structure["year"]
    ensure_structural_fees(academic_year=year, actor=accountant)
    months = iter_academic_months(year)
    assert len(months) >= 10

    client.force_login(accountant)
    _set_year(client, year)
    url = reverse(
        "finance:class-situation",
        kwargs={"public_id": academic_structure["school_class"].public_id},
    )
    response = client.get(url + f"?tableau={BOARD_MINERVAL}")
    assert response.status_code == 200
    assert response.context["board"] == BOARD_MINERVAL
    assert len(response.context["matrix"]["fees"]) == len(months)
    assert response.context["matrix"]["rows"]


@pytest.mark.django_db
def test_payment_blocks_overpay_and_redirects_to_earlier_month(
    accountant, academic_structure, enrolled_student
):
    from apps.finance.services.fee_structure_service import ensure_structural_fees
    from apps.finance.services.payment_sequence_service import (
        resolve_sequential_obligation,
    )

    year = academic_structure["year"]
    ensure_structural_fees(academic_year=year, actor=accountant)
    fees = list(
        SchoolFee.objects.filter(
            academic_year=year, category__code="MINERVAL"
        ).order_by("due_date")
    )
    assert len(fees) >= 2
    first, second = fees[0], fees[1]

    enrollment = enrolled_student["enrollment"]
    first_ob = StudentFeeObligation.objects.get(fee=first, enrollment=enrollment)
    record_payment(
        enrollment=enrollment,
        amount_total=Decimal("30000.00"),
        payment_date=date(2026, 10, 1),
        payment_method=Payment.PaymentMethod.CASH,
        allocations=[{"obligation": first_ob, "amount": Decimal("30000.00")}],
        actor=accountant,
    )
    first_ob.refresh_from_db()
    assert first_ob.amount_remaining == Decimal("20000.00")

    target, redirected = resolve_sequential_obligation(
        enrollment=enrollment, selected_fee=second
    )
    assert redirected is True
    assert target.fee_id == first.pk
    assert target.amount_remaining == Decimal("20000.00")

    with pytest.raises(FinanceError):
        record_payment(
            enrollment=enrollment,
            amount_total=Decimal("25000.00"),
            payment_date=date(2026, 10, 2),
            payment_method=Payment.PaymentMethod.CASH,
            allocations=[{"obligation": target, "amount": Decimal("25000.00")}],
            actor=accountant,
        )


@pytest.mark.django_db
def test_amount_in_words_fr_basic():
    from decimal import Decimal

    from apps.finance.services.receipt_service import amount_in_words_fr

    assert "cinquante mille" in amount_in_words_fr(Decimal("50000"), "CDF").lower()
    assert "francs congolais" in amount_in_words_fr(Decimal("20000"), "CDF").lower()


@pytest.mark.django_db
def test_receipt_pdf_is_compact_landscape(accountant, academic_structure, enrolled_student):
    from apps.finance.models import Payment
    from apps.finance.services.fee_structure_service import ensure_structural_fees
    from apps.finance.services.payment_service import record_payment
    from apps.finance.services.receipt_service import RECEIPT_SIZE, build_receipt_pdf
    from reportlab.lib.units import mm

    year = academic_structure["year"]
    ensure_structural_fees(academic_year=year, actor=accountant)
    enrollment = enrolled_student["enrollment"]
    obligation = StudentFeeObligation.objects.filter(enrollment=enrollment).first()
    assert obligation is not None
    payment = record_payment(
        enrollment=enrollment,
        amount_total=Decimal("10000.00"),
        payment_date=date(2026, 10, 1),
        payment_method=Payment.PaymentMethod.CASH,
        allocations=[{"obligation": obligation, "amount": Decimal("10000.00")}],
        actor=accountant,
    )
    content = build_receipt_pdf(payment=payment, audit=False)
    assert content.startswith(b"%PDF")
    assert RECEIPT_SIZE == (155 * mm, 102 * mm)
    assert len(content) > 500


@pytest.mark.django_db
def test_payable_fee_groups_names_then_periods(accountant, academic_structure):
    from apps.finance.services.fee_structure_service import ensure_structural_fees
    from apps.finance.services.payment_sequence_service import build_payable_fee_groups

    year = academic_structure["year"]
    ensure_structural_fees(academic_year=year, actor=accountant)
    fees = list(
        SchoolFee.objects.filter(academic_year=year, status=SchoolFee.Status.APPROVED)
        .select_related("category")
        .order_by("code")
    )
    groups = build_payable_fee_groups(fees)
    by_key = {g["key"]: g for g in groups}
    assert "MINERVAL" in by_key
    assert by_key["MINERVAL"]["label"] == "Minerval"
    assert by_key["MINERVAL"]["schedule_mode"] == SchoolFee.ScheduleMode.MONTHS
    assert len(by_key["MINERVAL"]["periods"]) >= 10
    assert "FRAIS_ETAT" in by_key
    assert by_key["FRAIS_ETAT"]["label"] == "Frais de l'État"
    assert by_key["FRAIS_ETAT"]["schedule_mode"] == SchoolFee.ScheduleMode.TRANCHES
    assert len(by_key["FRAIS_ETAT"]["periods"]) == 3


@pytest.mark.django_db
def test_payable_fee_groups_for_enrollment_hides_paid_periods(
    accountant, academic_structure, enrolled_student
):
    from apps.finance.services.fee_structure_service import (
        ensure_structural_fees,
        payable_fees_for_class,
    )
    from apps.finance.services.payment_sequence_service import (
        build_payable_fee_groups,
        build_payable_fee_groups_for_enrollment,
    )

    year = academic_structure["year"]
    school_class = academic_structure["school_class"]
    enrollment = enrolled_student["enrollment"]
    ensure_structural_fees(academic_year=year, actor=accountant)
    fees = payable_fees_for_class(school_class=school_class)
    all_groups = build_payable_fee_groups(fees)
    minerval_all = next(g for g in all_groups if g["key"] == "MINERVAL")
    assert len(minerval_all["periods"]) >= 2

    first_fee = minerval_all["fees"][0]
    obligation = StudentFeeObligation.objects.get(fee=first_fee, enrollment=enrollment)
    record_payment(
        enrollment=enrollment,
        amount_total=obligation.amount_due,
        payment_date=date(2026, 10, 1),
        payment_method=Payment.PaymentMethod.CASH,
        allocations=[{"obligation": obligation, "amount": obligation.amount_due}],
        actor=accountant,
    )

    filtered = build_payable_fee_groups_for_enrollment(
        enrollment=enrollment,
        fees=fees,
    )
    minerval_open = next(g for g in filtered if g["key"] == "MINERVAL")
    open_ids = {p["id"] for p in minerval_open["periods"]}
    assert first_fee.pk not in open_ids
    assert len(minerval_open["periods"]) == len(minerval_all["periods"]) - 1


@pytest.mark.django_db
def test_payment_matricule_lookup_returns_open_periods_only(
    client, accountant, academic_structure, enrolled_student
):
    from apps.finance.services.fee_structure_service import ensure_structural_fees
    from apps.secretariat.services.year_context import SESSION_KEY

    year = academic_structure["year"]
    enrollment = enrolled_student["enrollment"]
    student = enrolled_student["student"]
    ensure_structural_fees(academic_year=year, actor=accountant)

    first_ob = (
        StudentFeeObligation.objects.filter(enrollment=enrollment)
        .select_related("fee")
        .order_by("fee__due_date", "fee__period_index")
        .first()
    )
    assert first_ob is not None
    record_payment(
        enrollment=enrollment,
        amount_total=first_ob.amount_due,
        payment_date=date(2026, 10, 1),
        payment_method=Payment.PaymentMethod.CASH,
        allocations=[{"obligation": first_ob, "amount": first_ob.amount_due}],
        actor=accountant,
    )

    client.force_login(accountant)
    session = client.session
    session[SESSION_KEY] = year.pk
    session.save()

    from apps.finance.services.matricule_lookup import class_matricule_stem

    school_class = enrolled_student["enrollment"].school_class
    student = enrolled_student["student"]
    stem = class_matricule_stem(school_class=school_class)
    suffix = student.matricule[len(stem) :] if student.matricule.startswith(stem) else student.matricule
    response = client.get(
        reverse("finance:payment-matricule-lookup"),
        {"suffix": suffix, "stem": stem},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["student"]["name"]
    assert payload["student"]["class_name"]
    period_ids = {
        period["id"]
        for group in payload["fee_groups"]
        for period in group["periods"]
    }
    assert first_ob.fee_id not in period_ids


@pytest.mark.django_db
def test_secretary_fee_approval_list(client, secretary, academic_structure):
    client.force_login(secretary)
    _set_year(client, academic_structure["year"])
    response = client.get(reverse("secretariat:fee-approvals"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_fee_amount_change_current_class_updates_obligations(
    accountant, secretary, academic_structure, enrolled_student
):
    from apps.finance.models import FeeAmountChangeRequest, FeeClassAmount
    from apps.finance.services.fee_amount_change_service import (
        approve_amount_change,
        effective_fee_amount,
        submit_amount_change,
    )
    from apps.finance.services.fee_structure_service import ensure_structural_fees

    year = academic_structure["year"]
    school_class = academic_structure["school_class"]
    ensure_structural_fees(academic_year=year, actor=accountant)
    fee = (
        SchoolFee.objects.filter(academic_year=year, category__code="MINERVAL")
        .order_by("due_date")
        .first()
    )
    assert fee is not None
    enrollment = enrolled_student["enrollment"]
    obligation = StudentFeeObligation.objects.get(fee=fee, enrollment=enrollment)
    assert obligation.amount_due == fee.amount

    record_payment(
        enrollment=enrollment,
        amount_total=Decimal("30000.00"),
        payment_date=date(2026, 10, 1),
        payment_method=Payment.PaymentMethod.CASH,
        allocations=[{"obligation": obligation, "amount": Decimal("30000.00")}],
        actor=accountant,
    )
    obligation.refresh_from_db()
    assert obligation.amount_remaining == fee.amount - Decimal("30000.00")

    change = submit_amount_change(
        fee=fee,
        origin_class=school_class,
        new_amount=Decimal("100000.00"),
        scope=FeeAmountChangeRequest.Scope.CURRENT_CLASS,
        actor=accountant,
    )
    assert change.status == FeeAmountChangeRequest.Status.PENDING

    approve_amount_change(change=change, actor=secretary)
    change.refresh_from_db()
    assert change.status == FeeAmountChangeRequest.Status.APPROVED
    assert FeeClassAmount.objects.filter(fee=fee, school_class=school_class).exists()
    assert effective_fee_amount(fee=fee, school_class=school_class) == Decimal("100000.00")

    obligation.refresh_from_db()
    assert obligation.amount_due == Decimal("100000.00")
    assert obligation.amount_paid == Decimal("30000.00")
    assert obligation.amount_remaining == Decimal("70000.00")
    assert obligation.status == StudentFeeObligation.Status.PARTIAL


@pytest.mark.django_db
def test_fee_amount_change_all_classes_updates_base_amount(
    accountant, secretary, academic_structure, enrolled_student
):
    from apps.finance.models import FeeAmountChangeRequest, FeeClassAmount
    from apps.finance.services.fee_amount_change_service import (
        approve_amount_change,
        submit_amount_change,
    )
    from apps.finance.services.fee_structure_service import ensure_structural_fees

    year = academic_structure["year"]
    school_class = academic_structure["school_class"]
    ensure_structural_fees(academic_year=year, actor=accountant)
    fee = (
        SchoolFee.objects.filter(academic_year=year, category__code="FRAIS_ETAT")
        .order_by("code")
        .first()
    )
    assert fee is not None

    change = submit_amount_change(
        fee=fee,
        origin_class=school_class,
        new_amount=Decimal("40000.00"),
        scope=FeeAmountChangeRequest.Scope.ALL_CLASSES,
        actor=accountant,
    )
    approve_amount_change(change=change, actor=secretary)
    fee.refresh_from_db()
    assert fee.amount == Decimal("40000.00")
    assert not FeeClassAmount.objects.filter(fee=fee).exists()

    obligation = StudentFeeObligation.objects.get(
        fee=fee, enrollment=enrolled_student["enrollment"]
    )
    assert obligation.amount_due == Decimal("40000.00")


@pytest.mark.django_db
def test_card_scan_resolves_to_student_situation(
    client, accountant, secretary, academic_structure, enrolled_student
):
    from apps.finance.services.card_scan_service import resolve_card_qr_for_finance
    from apps.secretariat.services.card_service import generate_card
    from apps.secretariat.services.year_context import SESSION_KEY

    year = academic_structure["year"]
    enrollment = enrolled_student["enrollment"]
    student = enrolled_student["student"]
    card = generate_card(enrollment=enrollment, actor=secretary)

    resolved = resolve_card_qr_for_finance(card.qr_identifier)
    assert resolved["matricule"] == student.matricule
    assert str(student.public_id) in resolved["redirect_url"]

    client.force_login(accountant)
    session = client.session
    session[SESSION_KEY] = year.pk
    session.save()

    response = client.post(
        reverse("finance:card-scan-resolve"),
        data={"qr": card.qr_identifier},
        content_type="application/json",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["redirect_url"] == reverse(
        "finance:student-situation", kwargs={"public_id": student.public_id}
    )

    bad = client.post(
        reverse("finance:card-scan-resolve"),
        data={"qr": "KAL-CARD-deadbeef"},
        content_type="application/json",
    )
    assert bad.status_code == 404
    assert bad.json()["ok"] is False
