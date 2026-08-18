"""Secretariat academic year context and entity action tests."""

from __future__ import annotations

from datetime import date

import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.accounts.services import ensure_system_roles
from apps.secretariat.models import (
    AcademicYear,
    Communication,
    CommunicationTarget,
    Enrollment,
    SchoolClass,
    SchoolLevel,
    Section,
    Student,
)
from apps.secretariat.services.academic_service import (
    create_academic_year,
    create_level,
    create_school_class,
    create_section,
    delete_section,
)
from apps.secretariat.services.communication_service import create_draft, pin, unpin
from apps.secretariat.services.enrollment_service import create_enrollment
from apps.secretariat.services.exceptions import SecretariatError
from apps.secretariat.services.student_service import create_student
from apps.secretariat.services.year_context import SESSION_KEY, year_context_service


@pytest.fixture
def roles(db):
    return ensure_system_roles()


@pytest.fixture
def secretary(roles):
    return User.objects.create_user(
        username="sec.year",
        password="TempPass123!",
        nom="Sec",
        prenom="Test",
        role=roles[Role.CODE_SECRETAIRE],
    )


@pytest.fixture
def years(db):
    # Create the secondary year first (inactive) so the open year can still be created.
    y2 = create_academic_year(
        label="2026-2027",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 7, 31),
        is_active=False,
    )
    y1 = create_academic_year(
        label="2025-2026",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_active=True,
    )
    return {"open": y1, "other": y2}


@pytest.fixture
def structure(years):
    level = create_level(name="1re", code="1R", order=1)
    section = create_section(name="Générale", code="GEN-Y")
    c1 = create_school_class(
        academic_year=years["open"],
        level=level,
        section=section,
        letter="A",
        name="1A",
        code="1A-25",
        max_capacity=30,
    )
    c2 = create_school_class(
        academic_year=years["other"],
        level=level,
        section=section,
        letter="B",
        name="1B",
        code="1B-26",
        max_capacity=30,
    )
    return {"level": level, "section": section, "class_open": c1, "class_other": c2}


@pytest.mark.django_db
def test_secretary_redirected_without_session_year(client, secretary, years):
    client.force_login(secretary)
    response = client.get(reverse("secretariat:classes"))
    assert response.status_code == 302
    assert reverse("secretariat:academic-year-select") in response.url


@pytest.mark.django_db
def test_selecting_year_stores_session_key(client, secretary, years):
    client.force_login(secretary)
    year = years["open"]
    response = client.post(reverse("secretariat:academic-year-choose", args=[year.public_id]))
    assert response.status_code == 302
    assert client.session.get(SESSION_KEY) == year.pk
    assert year_context_service.get_selected_year_id(client) == year.pk


@pytest.mark.django_db
def test_classes_filtered_by_year(client, secretary, years, structure):
    client.force_login(secretary)
    session = client.session
    session[SESSION_KEY] = years["open"].pk
    session.save()
    response = client.get(reverse("secretariat:classes"))
    assert response.status_code == 200
    classes = list(response.context["page_obj"])
    assert {c.pk for c in classes} == {structure["class_open"].pk}
    assert structure["class_other"].pk not in {c.pk for c in classes}


@pytest.mark.django_db
def test_closed_year_blocks_class_create(client, secretary, years, structure):
    year = years["open"]
    year.is_closed = True
    year.is_active = False
    year.save(update_fields=["is_closed", "is_active"])
    client.force_login(secretary)
    session = client.session
    session[SESSION_KEY] = year.pk
    session.save()
    response = client.post(
        reverse("secretariat:class-create"),
        {
            "level": structure["level"].pk,
            "section": structure["section"].pk,
            "letter": "B",
            "name": "2A",
            "code": "2A-25",
            "max_capacity": 25,
            "room": "",
            "description": "",
            "is_active": "on",
        },
    )
    assert response.status_code == 200
    assert not SchoolClass.objects.filter(code="2A-25").exists()
    form = response.context["form"]
    all_errors = list(form.non_field_errors()) + [
        e for errs in form.errors.values() for e in errs
    ]
    assert any("clôturée" in e for e in all_errors)


@pytest.mark.django_db
def test_pin_unpin_communication(secretary, years):
    year = years["open"]
    communication = create_draft(
        title="Avis",
        content="Contenu",
        targets=[{"target_type": CommunicationTarget.TargetType.ACADEMIC_YEAR, "academic_year": year}],
        actor=secretary,
    )
    pinned = pin(communication, actor=secretary)
    assert pinned.is_pinned is True
    assert pinned.pinned_at is not None
    assert pinned.pinned_by_id == secretary.pk
    unpinned = unpin(pinned, actor=secretary)
    assert unpinned.is_pinned is False
    assert unpinned.pinned_at is None
    assert unpinned.pinned_by_id is None


@pytest.mark.django_db
def test_section_delete_refused_when_used(structure):
    with pytest.raises(SecretariatError) as exc:
        delete_section(structure["section"])
    assert "Désactivez" in str(exc.value) or "options" in str(exc.value).lower() or "classes" in str(exc.value).lower()


@pytest.mark.django_db
def test_students_list_scoped_to_year_enrollments(client, secretary, years, structure):
    client.force_login(secretary)
    session = client.session
    session[SESSION_KEY] = years["open"].pk
    session.save()
    enrolled = create_student(
        nom="Enrolled",
        prenom="One",
        sexe=Student.Gender.MALE,
        date_naissance=date(2010, 1, 1),
        date_admission=date(2025, 9, 1),
    )
    other = create_student(
        nom="Other",
        prenom="Two",
        sexe=Student.Gender.FEMALE,
        date_naissance=date(2010, 2, 2),
        date_admission=date(2025, 9, 1),
    )
    create_enrollment(
        student=enrolled,
        school_class=structure["class_open"],
        enrollment_type=Enrollment.EnrollmentType.NEW,
        status=Enrollment.Status.VALIDATED,
    )
    response = client.get(reverse("secretariat:students"))
    assert response.status_code == 200
    ids = {s.pk for s in response.context["page_obj"]}
    assert enrolled.pk in ids
    assert other.pk not in ids
    response_all = client.get(reverse("secretariat:students") + "?scope=all")
    ids_all = {s.pk for s in response_all.context["page_obj"]}
    assert other.pk in ids_all
