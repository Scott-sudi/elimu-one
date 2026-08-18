"""BI module tests — overview KPIs and cancelled payment exclusion."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.services import ensure_system_roles
from apps.bi.services import financial_analytics_service, overview_service
from apps.finance.models import Payment, SchoolFee, StudentFeeObligation
from apps.finance.services.fee_approval_service import approve_fee
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
def prefet(roles):
    return User.objects.create_user(
        username="prefet1",
        password="TempPass123!",
        nom="Kalala",
        prenom="Joseph",
        role=roles[Role.CODE_PREFET],
    )


@pytest.fixture
def secretary(roles):
    return User.objects.create_user(
        username="secretaire_bi",
        password="TempPass123!",
        nom="Nzuzi",
        prenom="Marie",
        role=roles[Role.CODE_SECRETAIRE],
    )


@pytest.fixture
def accountant(roles):
    return User.objects.create_user(
        username="comptable_bi",
        password="TempPass123!",
        nom="Kabasele",
        prenom="Paul",
        role=roles[Role.CODE_COMPTABLE],
    )


@pytest.fixture
def academic_structure(db):
    year = create_academic_year(
        label="2026-2027-BI",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 7, 31),
        is_active=True,
    )
    level = create_level(name="Première secondaire BI", code="1SEC-BI", order=10)
    section = create_section(name="Générale BI", code="GEN-BI")
    school_class = create_school_class(
        academic_year=year,
        level=level,
        section=section,
        letter="A",
        name="1re A BI",
        code="1A-BI-2026",
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


def _approved_fee(academic_structure, accountant, secretary, amount=Decimal("100000.00")):
    categories = ensure_default_fee_categories()
    fee = create_draft_fee(
        academic_year=academic_structure["year"],
        category=categories[0],
        code="BI-SCOL1",
        label="Scolarité BI",
        amount=amount,
        actor=accountant,
    )
    submit_fee(fee=fee, actor=accountant)
    approve_fee(fee=fee, actor=secretary)
    fee.refresh_from_db()
    assert fee.status == SchoolFee.Status.APPROVED
    return fee


@pytest.mark.django_db
def test_overview_effectif_and_expected_amount(
    academic_structure, enrolled_student, accountant, secretary
):
    year = academic_structure["year"]
    fee = _approved_fee(academic_structure, accountant, secretary)
    obligation = StudentFeeObligation.objects.get(
        fee=fee, enrollment=enrolled_student["enrollment"]
    )
    assert obligation.amount_due == Decimal("100000.00")

    overview = overview_service.build_overview(year)
    assert overview["kpis"]["effectif_total"] == 1
    assert overview["kpis"]["classes_actives"] == 1
    assert overview["kpis"]["montant_attendu"] == Decimal("100000.00")
    assert overview["kpis"]["montant_encaisse"] == Decimal("0.00")
    assert overview["kpis"]["solde"] == Decimal("100000.00")


@pytest.mark.django_db
def test_cancelled_payments_excluded_from_collected(
    academic_structure, enrolled_student, accountant, secretary
):
    year = academic_structure["year"]
    fee = _approved_fee(academic_structure, accountant, secretary, amount=Decimal("50000.00"))
    obligation = StudentFeeObligation.objects.get(fee=fee)

    payment = record_payment(
        enrollment=enrolled_student["enrollment"],
        amount_total=Decimal("20000.00"),
        payment_date=date(2026, 10, 1),
        payment_method=Payment.PaymentMethod.CASH,
        allocations=[{"obligation": obligation, "amount": Decimal("20000.00")}],
        actor=accountant,
    )
    assert payment.status == Payment.Status.VALID

    overview = overview_service.build_overview(year)
    assert overview["kpis"]["montant_encaisse"] == Decimal("20000.00")

    cancel_payment(payment=payment, reason="Erreur de saisie", actor=accountant)
    payment.refresh_from_db()
    assert payment.status == Payment.Status.CANCELLED

    overview_after = overview_service.build_overview(year)
    assert overview_after["kpis"]["montant_encaisse"] == Decimal("0.00")

    financial = financial_analytics_service.build_financial_analytics(year)
    assert financial["kpis"]["montant_encaisse"] == Decimal("0.00")
    assert financial["kpis"]["paiements_annules"] == 1


@pytest.mark.django_db
def test_bi_overview_page_requires_prefet(client, prefet, academic_structure):
    _set_year(client, academic_structure["year"])
    response = client.get(reverse("bi:overview"))
    assert response.status_code in (302, 403)

    client.force_login(prefet)
    response = client.get(reverse("bi:overview"))
    assert response.status_code == 200
    assert response.context["kpis"]["effectif_total"] == 0


@pytest.mark.django_db
def test_bi_overview_api(prefet, academic_structure, enrolled_student):
    client = APIClient()
    client.force_authenticate(user=prefet)
    session = client.session
    session[SESSION_KEY] = academic_structure["year"].pk
    session.save()

    response = client.get("/api/v1/bi/overview/")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["kpis"]["effectif_total"] == 1
