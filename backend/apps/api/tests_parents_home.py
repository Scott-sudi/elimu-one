"""Tests for parents mobile home overview API."""

from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.secretariat.models import Enrollment, Student, StudentGuardian
from apps.secretariat.services.academic_service import (
    create_academic_year,
    create_level,
    create_school_class,
    create_section,
)
from apps.secretariat.services.enrollment_service import create_enrollment
from apps.secretariat.services.guardian_service import link_responsable_to_student
from apps.secretariat.services.student_service import create_student


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def guardian_with_child(db):
    year = create_academic_year(
        label="2025-2026-H",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_active=True,
    )
    level = create_level(name="4ème", code="4E-H", order=4)
    section = create_section(name="Scientifique", code="SCI-H")
    school_class = create_school_class(
        academic_year=year,
        level=level,
        section=section,
        letter="A",
        name="4ème Scientifique",
        code="4SCI-H",
        max_capacity=40,
    )
    student = create_student(
        nom="Kalunga",
        prenom="Jean",
        sexe=Student.Gender.MALE,
        date_naissance=date(2010, 5, 1),
        date_admission=date(2025, 9, 1),
    )
    create_enrollment(
        student=student,
        school_class=school_class,
        enrollment_type=Enrollment.EnrollmentType.NEW,
        enrollment_date=date(2025, 9, 1),
    )
    link = link_responsable_to_student(
        student=student,
        full_name="Marie Kabasele",
        telephone_principal="+243970000111",
        lien_parente=StudentGuardian.Relationship.MOTHER,
    )
    return {"guardian": link.guardian, "student": student, "year": year}


@pytest.mark.django_db
def test_home_overview_returns_live_guardian_name(api, guardian_with_child):
    guardian = guardian_with_child["guardian"]
    guardian.prenom = "Paul"
    guardian.nom = "Mwamba"
    guardian.save(update_fields=["prenom", "nom", "updated_at"])

    gid = str(guardian.public_id)
    response = api.get(f"/api/v1/parents/home/overview/?guardian_public_id={gid}")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["display_name"] == "Paul Mwamba"
    assert data["children_count"] == 1
    assert "2025-2026-H" in data["school_year_label"]
    assert data["unpaid_balance_label"] == "Aucun"
    assert data["general_average_percent"] is None
    assert data["activities"] == []


@pytest.mark.django_db
def test_home_overview_requires_guardian_id(api):
    response = api.get("/api/v1/parents/home/overview/")
    assert response.status_code == 400
    assert response.json()["success"] is False


@pytest.mark.django_db
def test_home_overview_unknown_guardian(api):
    response = api.get(
        "/api/v1/parents/home/overview/?guardian_public_id="
        "00000000-0000-0000-0000-000000000099"
    )
    assert response.status_code == 404
