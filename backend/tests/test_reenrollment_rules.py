"""Tests for inscription vs réinscription progression rules."""

from __future__ import annotations

from datetime import date

import pytest
from django.urls import reverse

from apps.secretariat.models import AcademicYear, Enrollment
from apps.secretariat.services.academic_service import (
    close_academic_year,
    create_academic_year,
    create_level,
    create_school_class,
    create_section,
)
from apps.secretariat.services.enrollment_number_service import generate_enrollment_number
from apps.secretariat.services.enrollment_service import create_enrollment
from apps.secretariat.services.exceptions import SecretariatError
from apps.secretariat.services.reenrollment_service import (
    eligible_reenrollments_for_class,
    reenroll_student,
)
from apps.secretariat.services.student_service import create_student
from apps.secretariat.services.year_context import SESSION_KEY
from apps.accounts.models import Role, User
from apps.accounts.services import ensure_system_roles


@pytest.fixture
def roles(db):
    return ensure_system_roles()


@pytest.fixture
def secretary(roles):
    return User.objects.create_user(
        username="secretaire-reenrol",
        password="TempPass123!",
        nom="Nzuzi",
        prenom="Marie",
        role=roles[Role.CODE_SECRETAIRE],
    )


def _past_enrollment(*, student, school_class, actor=None) -> Enrollment:
    """Create a historical enrollment even if the year is already closed."""
    return Enrollment.objects.create(
        student=student,
        academic_year=school_class.academic_year,
        school_class=school_class,
        enrollment_number=generate_enrollment_number(
            year=school_class.academic_year.start_date.year
        ),
        enrollment_type=Enrollment.EnrollmentType.NEW,
        enrollment_date=school_class.academic_year.start_date,
        status=Enrollment.Status.VALIDATED,
        created_by=actor,
    )


@pytest.fixture
def progression(db, secretary):
    prev_year = create_academic_year(
        label="2024-2025",
        start_date=date(2024, 9, 1),
        end_date=date(2025, 7, 31),
        is_active=True,
    )
    close_academic_year(prev_year, actor=secretary)
    curr_year = create_academic_year(
        label="2025-2026",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_active=True,
    )

    level_7 = create_level(name="7ème année", code="7E-T", order=1)
    level_8 = create_level(name="8ème année", code="8E-T", order=2)
    level_1 = create_level(name="1ère année", code="1E-T", order=3)
    section = create_section(name="Tronc test", code="TRT")

    class_7_prev = create_school_class(
        academic_year=prev_year,
        level=level_7,
        section=None,
        letter="A",
        name="7ème A",
        code="7A-2425",
        max_capacity=40,
    )
    class_8_curr = create_school_class(
        academic_year=curr_year,
        level=level_8,
        section=None,
        letter="A",
        name="8ème A",
        code="8A-2526",
        max_capacity=40,
    )
    class_1_curr = create_school_class(
        academic_year=curr_year,
        level=level_1,
        section=section,
        letter="A",
        name="1ère SCI A",
        code="1SCI-2526",
        max_capacity=40,
    )
    return {
        "prev_year": prev_year,
        "curr_year": curr_year,
        "class_7_prev": class_7_prev,
        "class_8_curr": class_8_curr,
        "class_1_curr": class_1_curr,
        "level_7": level_7,
        "level_8": level_8,
        "level_1": level_1,
    }


@pytest.mark.django_db
def test_reenroll_requires_previous_closed_year_and_next_level(progression, secretary):
    student = create_student(
        nom="Kalala",
        prenom="Grace",
        sexe="F",
        date_naissance=date(2012, 5, 5),
        date_admission=date(2024, 9, 1),
    )
    previous = _past_enrollment(
        student=student,
        school_class=progression["class_7_prev"],
        actor=secretary,
    )

    renewed = reenroll_student(
        previous_enrollment=previous,
        target_class=progression["class_8_curr"],
        actor=secretary,
    )
    assert renewed.enrollment_type == Enrollment.EnrollmentType.RENEWAL
    assert renewed.school_class_id == progression["class_8_curr"].id

    student2 = create_student(
        nom="Ilunga",
        prenom="Jean",
        sexe="M",
        date_naissance=date(2012, 6, 6),
        date_admission=date(2024, 9, 1),
    )
    previous2 = _past_enrollment(
        student=student2,
        school_class=progression["class_7_prev"],
        actor=secretary,
    )
    with pytest.raises(SecretariatError):
        reenroll_student(
            previous_enrollment=previous2,
            target_class=progression["class_1_curr"],
            actor=secretary,
        )


@pytest.mark.django_db
def test_inscription_blocked_when_reenrollment_required(progression, secretary):
    student = create_student(
        nom="Mwamba",
        prenom="Sarah",
        sexe="F",
        date_naissance=date(2012, 7, 7),
        date_admission=date(2024, 9, 1),
    )
    _past_enrollment(
        student=student,
        school_class=progression["class_7_prev"],
        actor=secretary,
    )
    with pytest.raises(SecretariatError, match="réinscription"):
        create_enrollment(
            student=student,
            school_class=progression["class_8_curr"],
            enrollment_type=Enrollment.EnrollmentType.NEW,
            actor=secretary,
        )


@pytest.mark.django_db
def test_inscription_allowed_after_gap_year(progression, secretary):
    """Former student not present last year may use inscription (not réinscription)."""
    from apps.secretariat.models import SchoolClass

    older = AcademicYear.objects.create(
        label="2023-2024",
        start_date=date(2023, 9, 1),
        end_date=date(2024, 7, 31),
        is_active=False,
        is_closed=True,
    )
    class_7_older = SchoolClass.objects.create(
        academic_year=older,
        level=progression["level_7"],
        section=None,
        letter="B",
        name="7ème B",
        code="7B-2324",
        max_capacity=40,
    )
    student = create_student(
        nom="Retour",
        prenom="Paul",
        sexe="M",
        date_naissance=date(2011, 1, 1),
        date_admission=date(2023, 9, 1),
    )
    _past_enrollment(student=student, school_class=class_7_older, actor=secretary)
    enrollment = create_enrollment(
        student=student,
        school_class=progression["class_1_curr"],
        enrollment_type=Enrollment.EnrollmentType.NEW,
        actor=secretary,
    )
    assert enrollment.enrollment_type == Enrollment.EnrollmentType.NEW
    assert student.pk not in eligible_reenrollments_for_class(
        progression["class_1_curr"]
    ).values_list("student_id", flat=True)


@pytest.mark.django_db
def test_class_enroll_and_reenroll_views(client, secretary, progression):
    client.force_login(secretary)
    session = client.session
    session[SESSION_KEY] = progression["curr_year"].pk
    session.save()

    detail = client.get(
        reverse("secretariat:class-detail", args=[progression["class_8_curr"].public_id])
    )
    assert detail.status_code == 200
    body = detail.content.decode()
    assert "Inscription" in body
    assert "Réinscription" in body

    enroll_page = client.get(
        reverse("secretariat:class-enroll", args=[progression["class_8_curr"].public_id])
    )
    assert enroll_page.status_code == 200

    reenroll_page = client.get(
        reverse("secretariat:class-reenroll", args=[progression["class_8_curr"].public_id])
    )
    assert reenroll_page.status_code == 200
