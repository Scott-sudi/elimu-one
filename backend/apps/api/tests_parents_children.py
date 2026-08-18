"""Tests for parents mobile children list API."""

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
from apps.secretariat.services.guardian_service import create_guardian, link_responsable_to_student
from apps.secretariat.services.student_service import create_student


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def guardian_with_child(db):
    year = create_academic_year(
        label="2025-2026-P",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_active=True,
    )
    level = create_level(name="4ème", code="4E-P", order=4)
    section = create_section(name="Scientifique", code="SCI-P")
    school_class = create_school_class(
        academic_year=year,
        level=level,
        section=section,
        letter="A",
        name="4ème Scientifique",
        code="4SCI-P",
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
        full_name="Scott Sudi",
        telephone_principal="+243979867103",
        lien_parente=StudentGuardian.Relationship.FATHER,
    )
    return {"guardian": link.guardian, "student": student}


@pytest.mark.django_db
def test_list_children_for_guardian(api, guardian_with_child):
    gid = str(guardian_with_child["guardian"].public_id)
    response = api.get(f"/api/v1/parents/children/?guardian_public_id={gid}")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    enfants = body["data"]["enfants"]
    assert len(enfants) == 1
    assert enfants[0]["matricule"] == guardian_with_child["student"].matricule
    assert "Jean" in enfants[0]["nom"]
    assert enfants[0]["classe"] == "4ème Scientifique"
    assert enfants[0]["actif"] is True


@pytest.mark.django_db
def test_list_children_via_header(api, guardian_with_child):
    gid = str(guardian_with_child["guardian"].public_id)
    response = api.get(
        "/api/v1/parents/children/",
        HTTP_X_GUARDIAN_PUBLIC_ID=gid,
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["enfants"]) == 1


@pytest.mark.django_db
def test_list_children_missing_guardian(api):
    response = api.get("/api/v1/parents/children/")
    assert response.status_code == 400


@pytest.mark.django_db
def test_list_children_unknown_guardian(api):
    response = api.get(
        "/api/v1/parents/children/?guardian_public_id=00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 404
