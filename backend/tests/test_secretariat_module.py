"""Secretariat module tests."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.services import create_initial_administrator, ensure_system_roles
from apps.audit.models import AuditLog
from apps.secretariat.models import (
    AcademicYear,
    Enrollment,
    Guardian,
    SchoolClass,
    SchoolLevel,
    Section,
    Student,
    StudentCard,
    StudentGuardian,
)
from apps.secretariat.services.academic_service import (
    activate_academic_year,
    close_academic_year,
    create_academic_year,
    create_level,
    create_school_class,
    create_section,
)
from apps.secretariat.services.card_service import generate_card
from apps.secretariat.services.enrollment_service import create_enrollment
from apps.secretariat.services.exceptions import SecretariatError
from apps.secretariat.services.guardian_service import associate_guardian, create_guardian
from apps.secretariat.services.student_service import create_student
from apps.secretariat.services.transfer_service import transfer_student


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
        name="1re A",
        code="1A-2026",
        max_capacity=2,
    )
    return {
        "year": year,
        "level": level,
        "section": section,
        "school_class": school_class,
    }


@pytest.mark.django_db
def test_matricule_unique_generation():
    s1 = create_student(
        nom="A",
        prenom="Un",
        sexe=Student.Gender.MALE,
        date_naissance=date(2010, 1, 1),
        date_admission=date(2026, 9, 1),
    )
    s2 = create_student(
        nom="B",
        prenom="Deux",
        sexe=Student.Gender.FEMALE,
        date_naissance=date(2010, 2, 2),
        date_admission=date(2026, 9, 1),
    )
    assert s1.matricule != s2.matricule
    assert s1.matricule.startswith("KAL-")
    assert s2.matricule.startswith("KAL-")


@pytest.mark.django_db
def test_single_active_academic_year():
    y1 = create_academic_year(
        label="2025-2026",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_active=True,
    )
    y2 = create_academic_year(
        label="2026-2027",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 7, 31),
        is_active=True,
    )
    y1.refresh_from_db()
    assert not y1.is_active
    assert y2.is_active
    activate_academic_year(y1)
    y1.refresh_from_db()
    y2.refresh_from_db()
    assert y1.is_active
    assert not y2.is_active
    assert AcademicYear.objects.filter(is_active=True).count() == 1


@pytest.mark.django_db
def test_academic_year_invalid_dates():
    with pytest.raises(SecretariatError):
        create_academic_year(
            label="BAD",
            start_date=date(2027, 1, 1),
            end_date=date(2026, 1, 1),
        )


@pytest.mark.django_db
def test_close_academic_year(academic_structure):
    year = academic_structure["year"]
    close_academic_year(year)
    year.refresh_from_db()
    assert year.is_closed
    assert not year.is_active
    assert AuditLog.objects.filter(action=AuditLog.Action.ACADEMIC_CLOSED).exists()


@pytest.mark.django_db
def test_class_code_unique_per_year(academic_structure):
    with pytest.raises(Exception):
        create_school_class(
            academic_year=academic_structure["year"],
            level=academic_structure["level"],
            section=academic_structure["section"],
            name="1re B",
            code="1A-2026",
            max_capacity=30,
        )


@pytest.mark.django_db
def test_student_guardian_primary_and_enrollment(academic_structure, secretary):
    student = create_student(
        nom="Ilunga",
        postnom="Mukendi",
        prenom="Grace",
        sexe=Student.Gender.FEMALE,
        date_naissance=date(2012, 5, 4),
        date_admission=date(2026, 9, 1),
        actor=secretary,
    )
    assert student.matricule
    guardian = create_guardian(
        nom="Ilunga",
        prenom="Jean",
        telephone_principal="0812345678",
        actor=secretary,
    )
    link = associate_guardian(
        student=student,
        guardian=guardian,
        lien_parente=StudentGuardian.Relationship.FATHER,
        is_primary=True,
        actor=secretary,
    )
    assert link.is_primary

    enrollment = create_enrollment(
        student=student,
        school_class=academic_structure["school_class"],
        enrollment_type=Enrollment.EnrollmentType.NEW,
        actor=secretary,
    )
    assert enrollment.enrollment_number.startswith("INS-")
    assert enrollment.status == Enrollment.Status.VALIDATED

    with pytest.raises(SecretariatError):
        create_enrollment(
            student=student,
            school_class=academic_structure["school_class"],
            enrollment_type=Enrollment.EnrollmentType.NEW,
            actor=secretary,
        )


@pytest.mark.django_db
def test_capacity_and_transfer(academic_structure, secretary):
    year = academic_structure["year"]
    level = academic_structure["level"]
    section = academic_structure["section"]
    class_a = academic_structure["school_class"]
    class_b = create_school_class(
        academic_year=year,
        level=level,
        section=section,
        name="1re B",
        code="1B-2026",
        max_capacity=30,
    )

    students = []
    for i in range(2):
        student = create_student(
            nom=f"Nom{i}",
            prenom=f"Prenom{i}",
            sexe=Student.Gender.MALE,
            date_naissance=date(2011, 1, 1),
            date_admission=date(2026, 9, 1),
        )
        students.append(student)
        create_enrollment(
            student=student,
            school_class=class_a,
            enrollment_type=Enrollment.EnrollmentType.NEW,
            actor=secretary,
        )

    extra = create_student(
        nom="Extra",
        prenom="Eleve",
        sexe=Student.Gender.MALE,
        date_naissance=date(2011, 2, 2),
        date_admission=date(2026, 9, 1),
    )
    with pytest.raises(SecretariatError):
        create_enrollment(
            student=extra,
            school_class=class_a,
            enrollment_type=Enrollment.EnrollmentType.NEW,
            actor=secretary,
        )

    enrollment = Enrollment.objects.get(student=students[0], status=Enrollment.Status.VALIDATED)
    transfer = transfer_student(
        enrollment=enrollment,
        to_class=class_b,
        motif="Rééquilibrage",
        actor=secretary,
    )
    enrollment.refresh_from_db()
    assert enrollment.school_class_id == class_b.id
    assert transfer.from_class_id == class_a.id


@pytest.mark.django_db
def test_card_qr_unique_and_opaque(academic_structure, secretary):
    student = create_student(
        nom="Kart",
        prenom="Eleve",
        sexe=Student.Gender.MALE,
        date_naissance=date(2010, 3, 3),
        date_admission=date(2026, 9, 1),
    )
    enrollment = create_enrollment(
        student=student,
        school_class=academic_structure["school_class"],
        enrollment_type=Enrollment.EnrollmentType.NEW,
        actor=secretary,
    )
    card = generate_card(enrollment=enrollment, actor=secretary)
    assert card.qr_identifier.startswith("KAL-CARD-")
    assert student.nom not in card.qr_identifier
    assert StudentCard.objects.filter(qr_identifier=card.qr_identifier).count() == 1
    assert card.qr_image
    assert card.pdf_file


@pytest.mark.django_db
def test_views_permissions(client, secretary, accountant, academic_structure):
    url = reverse("secretariat:dashboard")
    assert client.get(url).status_code in (302, 403)

    client.force_login(accountant)
    assert client.get(url).status_code == 403

    client.force_login(secretary)
    assert client.get(url).status_code == 200
    assert client.get(reverse("secretariat:students")).status_code == 200
    assert client.get(reverse("secretariat:academic-years")).status_code == 200

    htmx = client.get(reverse("secretariat:students"), HTTP_HX_REQUEST="true")
    assert htmx.status_code == 200


@pytest.mark.django_db
def test_api_secretary_and_card_resolve(secretary, accountant, academic_structure):
    student = create_student(
        nom="Api",
        prenom="Eleve",
        sexe=Student.Gender.FEMALE,
        date_naissance=date(2012, 8, 8),
        date_admission=date(2026, 9, 1),
    )
    enrollment = create_enrollment(
        student=student,
        school_class=academic_structure["school_class"],
        enrollment_type=Enrollment.EnrollmentType.NEW,
        actor=secretary,
    )
    card = generate_card(enrollment=enrollment, actor=secretary)

    api = APIClient()
    api.force_authenticate(user=accountant)
    denied = api.get("/api/v1/secretariat/students/")
    assert denied.status_code == 403

    api.force_authenticate(user=secretary)
    listing = api.get("/api/v1/secretariat/students/")
    assert listing.status_code == 200

    resolve = api.get(f"/api/v1/cards/resolve/{card.qr_identifier}/")
    assert resolve.status_code == 200
    payload = resolve.json()
    data = payload.get("data", payload)
    assert data.get("matricule") == student.matricule
    assert "telephone_principal" not in data
    assert "allergies" not in data
    assert "adresse" not in data
    assert "date_naissance" not in data
