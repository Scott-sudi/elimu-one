from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.api.models import ParentNotificationRead
from apps.api.parents_notifications import build_parent_notifications
from apps.discipline.models import (
    AbsenceJustification,
    ClassAttendanceSheet,
    ConductCategory,
    DailyAttendance,
    DisciplinaryIncident,
    DisciplinaryMeasure,
    DisciplinaryMeasureType,
    ExitAuthorization,
    IncidentParticipant,
    ParentSummons,
)
from apps.discipline.services.parent_notification_policy import notification_variant
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
def family(db):
    today = timezone.localdate()
    year = create_academic_year(
        label="Notifications parents",
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=300),
        is_active=True,
    )
    level = create_level(name="Notif niveau", code="NOTIF", order=1)
    section = create_section(name="Notif section", code="NOTIF")
    school_class = create_school_class(
        academic_year=year,
        level=level,
        section=section,
        letter="A",
        name="Classe notifications",
        code="NOTIF",
        max_capacity=40,
    )

    def add_student(suffix: str, phone: str):
        student = create_student(
            nom=f"Nom{suffix}",
            prenom=f"Prenom{suffix}",
            sexe=Student.Gender.MALE,
            date_naissance=today - timedelta(days=4000),
            date_admission=today - timedelta(days=30),
        )
        enrollment = create_enrollment(
            student=student,
            school_class=school_class,
            enrollment_type=Enrollment.EnrollmentType.NEW,
            enrollment_date=today - timedelta(days=30),
        )
        enrollment.status = Enrollment.Status.VALIDATED
        enrollment.save(update_fields=["status", "updated_at"])
        link = link_responsable_to_student(
            student=student,
            full_name=f"Parent {suffix}",
            telephone_principal=phone,
            lien_parente=StudentGuardian.Relationship.FATHER,
        )
        return student, enrollment, link.guardian

    main, main_enrollment, guardian = add_student("Main", "0990000001")
    participant, participant_enrollment, participant_guardian = add_student(
        "Participant", "0990000002"
    )
    unrelated, _, unrelated_guardian = add_student("Other", "0990000003")
    category = ConductCategory.objects.create(code="INC-N", name="Incident")
    return {
        "today": today,
        "year": year,
        "class": school_class,
        "student": main,
        "enrollment": main_enrollment,
        "guardian": guardian,
        "participant": participant,
        "participant_enrollment": participant_enrollment,
        "participant_guardian": participant_guardian,
        "unrelated": unrelated,
        "unrelated_guardian": unrelated_guardian,
        "category": category,
    }


def _incident(family, *, status):
    return DisciplinaryIncident.objects.create(
        academic_year=family["year"],
        student=family["student"],
        school_class=family["class"],
        category=family["category"],
        title="Incident privé",
        description="Description qui ne doit pas révéler les autres élèves",
        incident_date=family["today"],
        status=status,
    )


@pytest.mark.django_db
def test_policy_ignores_preparation_and_marks_official_updates():
    assert (
        notification_variant(
            kind="incident",
            current_status=DisciplinaryIncident.Status.REVIEW,
            previous_status=DisciplinaryIncident.Status.DRAFT,
            created=False,
            meaningful_changed=True,
        )
        is None
    )
    assert (
        notification_variant(
            kind="incident",
            current_status=DisciplinaryIncident.Status.CONFIRMED,
            previous_status=DisciplinaryIncident.Status.REVIEW,
            created=False,
            meaningful_changed=False,
        )
        == "new"
    )
    assert (
        notification_variant(
            kind="incident",
            current_status=DisciplinaryIncident.Status.CLOSED,
            previous_status=DisciplinaryIncident.Status.CONFIRMED,
            created=False,
            meaningful_changed=False,
        )
        == "updated"
    )


@pytest.mark.django_db
def test_inbox_contains_only_official_discipline_types(family):
    _incident(family, status=DisciplinaryIncident.Status.DRAFT)
    official = _incident(family, status=DisciplinaryIncident.Status.CONFIRMED)
    measure_type = DisciplinaryMeasureType.objects.create(
        code="RAPPEL-N", name="Rappel"
    )
    DisciplinaryMeasure.objects.create(
        incident=official,
        student=family["student"],
        measure_type=measure_type,
        status=DisciplinaryMeasure.Status.PROPOSED,
    )
    DisciplinaryMeasure.objects.create(
        incident=official,
        student=family["student"],
        measure_type=measure_type,
        status=DisciplinaryMeasure.Status.VALIDATED,
    )
    ParentSummons.objects.create(
        academic_year=family["year"],
        student=family["student"],
        summon_number="SUM-DRAFT",
        reason="Préparation",
        summon_date=family["today"],
        status=ParentSummons.Status.SCHEDULED,
    )
    ParentSummons.objects.create(
        academic_year=family["year"],
        student=family["student"],
        summon_number="SUM-SENT",
        reason="Transmise",
        summon_date=family["today"],
        status=ParentSummons.Status.SENT,
    )
    ExitAuthorization.objects.create(
        academic_year=family["year"],
        student=family["student"],
        enrollment=family["enrollment"],
        date=family["today"],
        reason="Rendez-vous",
        status=ExitAuthorization.Status.AUTHORIZED,
    )
    attendance = DailyAttendance.objects.create(
        academic_year=family["year"],
        enrollment=family["enrollment"],
        student=family["student"],
        date=family["today"],
        status=DailyAttendance.Status.ABSENT,
    )
    AbsenceJustification.objects.create(
        attendance=attendance,
        reason="Maladie",
        status=AbsenceJustification.Status.ACCEPTED,
    )

    sources = [
        item["source"]
        for item in build_parent_notifications(
            guardian=family["guardian"], limit=40
        )["items"]
    ]
    assert sources.count("discipline_incident") == 1
    assert sources.count("discipline_measure") == 1
    assert sources.count("discipline_summons") == 1
    assert "discipline_exit" in sources
    assert "discipline_justification" in sources


@pytest.mark.django_db
def test_all_attendance_statuses_require_validated_sheet(family):
    for offset, status in enumerate(DailyAttendance.Status.values):
        day = family["today"] - timedelta(days=offset)
        DailyAttendance.objects.create(
            academic_year=family["year"],
            enrollment=family["enrollment"],
            student=family["student"],
            date=day,
            status=status,
        )
        ClassAttendanceSheet.objects.create(
            academic_year=family["year"],
            school_class=family["class"],
            date=day,
            status=(
                ClassAttendanceSheet.Status.DRAFT
                if offset == 0
                else ClassAttendanceSheet.Status.VALIDATED
            ),
        )
    items = build_parent_notifications(
        guardian=family["guardian"], limit=40
    )["items"]
    attendance_items = [
        item for item in items if item["source"] == "discipline_attendance"
    ]
    assert len(attendance_items) == len(DailyAttendance.Status.values) - 1
    assert {item["title"] for item in attendance_items}


@pytest.mark.django_db
def test_participant_guardian_privacy_and_authorization(api, family):
    incident = _incident(
        family, status=DisciplinaryIncident.Status.CONFIRMED
    )
    IncidentParticipant.objects.create(
        incident=incident,
        student=family["participant"],
        role=IncidentParticipant.Role.WITNESS,
    )
    inbox = build_parent_notifications(
        guardian=family["participant_guardian"], limit=40
    )
    item = next(
        row for row in inbox["items"] if row["source"] == "discipline_incident"
    )
    assert "Témoin" in item["subtitle"]
    assert family["student"].prenom not in item["body"]

    url = f"/api/v1/parents/discipline/incident/{incident.public_id}/"
    allowed = api.get(
        url,
        HTTP_X_GUARDIAN_PUBLIC_ID=str(
            family["participant_guardian"].public_id
        ),
    )
    assert allowed.status_code == 200
    assert allowed.json()["data"]["role_label"] == "Témoin"
    assert family["student"].prenom not in allowed.json()["data"]["content"]
    denied = api.get(
        url,
        HTTP_X_GUARDIAN_PUBLIC_ID=str(family["unrelated_guardian"].public_id),
    )
    assert denied.status_code == 404


@pytest.mark.django_db
def test_targeted_summons_is_private_and_read_per_guardian(api, family):
    StudentGuardian.objects.create(
        student=family["student"],
        guardian=family["participant_guardian"],
        lien_parente=StudentGuardian.Relationship.OTHER,
        receives_notifications=True,
    )
    summons = ParentSummons.objects.create(
        academic_year=family["year"],
        student=family["student"],
        summon_number="SUM-TARGET",
        reason="Entretien confidentiel",
        summon_date=family["today"],
        status=ParentSummons.Status.SENT,
    )
    summons.target_guardians.add(family["guardian"])

    main_sources = {
        item["source_id"]
        for item in build_parent_notifications(
            guardian=family["guardian"], limit=40
        )["items"]
        if item["source"] == "discipline_summons"
    }
    other_sources = {
        item["source_id"]
        for item in build_parent_notifications(
            guardian=family["participant_guardian"], limit=40
        )["items"]
        if item["source"] == "discipline_summons"
    }
    assert str(summons.public_id) in main_sources
    assert str(summons.public_id) not in other_sources

    url = f"/api/v1/parents/discipline/summons/{summons.public_id}/"
    allowed = api.get(
        url,
        HTTP_X_GUARDIAN_PUBLIC_ID=str(family["guardian"].public_id),
    )
    denied = api.get(
        url,
        HTTP_X_GUARDIAN_PUBLIC_ID=str(
            family["participant_guardian"].public_id
        ),
    )
    assert allowed.status_code == 200
    assert denied.status_code == 404
    summons.refresh_from_db()
    assert summons.acknowledgement_date is None


@pytest.mark.django_db
def test_detail_and_mark_all_read_persist_and_updates_reopen(api, family):
    incident = _incident(
        family, status=DisciplinaryIncident.Status.CONFIRMED
    )
    gid = str(family["guardian"].public_id)
    detail_url = f"/api/v1/parents/discipline/incident/{incident.public_id}/"
    assert (
        api.get(detail_url, HTTP_X_GUARDIAN_PUBLIC_ID=gid).status_code == 200
    )
    assert ParentNotificationRead.objects.filter(
        guardian=family["guardian"],
        source="discipline_incident",
        source_id=str(incident.public_id),
    ).exists()
    assert build_parent_notifications(
        guardian=family["guardian"], limit=40
    )["unread_count"] == 0

    incident.title = "Modification officielle"
    incident.save(update_fields=["title", "updated_at"])
    assert build_parent_notifications(
        guardian=family["guardian"], limit=40
    )["unread_count"] == 1

    response = api.post(
        "/api/v1/parents/notifications/",
        {"guardian_public_id": gid},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["data"]["unread_count"] == 0
    assert (
        ParentNotificationRead.objects.filter(
            guardian=family["guardian"],
            source="discipline_incident",
            source_id=str(incident.public_id),
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_push_dedupe_and_official_measure_variant(family, monkeypatch):
    import sys
    from unittest.mock import MagicMock

    sys.modules.setdefault("requests", MagicMock())
    from apps.api import parents_push

    parents_push._recent_push_keys.clear()
    assert parents_push._claim_push_key("discipline_measure:abc:1") is True
    assert parents_push._claim_push_key("discipline_measure:abc:1") is False
    assert parents_push._claim_push_key("discipline_measure:abc:2") is True

    sent = []

    def fake_send(*, guardians, title, body, data=None):
        sent.append({"title": title, "data": data or {}})
        return 1

    monkeypatch.setattr(parents_push, "send_push_to_guardians", fake_send)
    measure_type = DisciplinaryMeasureType.objects.create(
        code="AVERT-N", name="Avertissement"
    )
    incident = _incident(family, status=DisciplinaryIncident.Status.CONFIRMED)
    draft = DisciplinaryMeasure.objects.create(
        incident=incident,
        student=family["student"],
        measure_type=measure_type,
        status=DisciplinaryMeasure.Status.PROPOSED,
    )
    assert parents_push.notify_guardians_of_measure(measure=draft) == 0
    assert sent == []

    official = DisciplinaryMeasure.objects.create(
        incident=incident,
        student=family["student"],
        measure_type=measure_type,
        status=DisciplinaryMeasure.Status.VALIDATED,
    )
    assert parents_push.notify_guardians_of_measure(measure=official) == 1
    assert len(sent) == 1
    assert sent[0]["data"]["type"] == "discipline_measure"
    assert (
        notification_variant(
            kind="measure",
            current_status=DisciplinaryMeasure.Status.VALIDATED,
            previous_status=DisciplinaryMeasure.Status.PROPOSED,
            created=False,
            meaningful_changed=False,
        )
        == "new"
    )

