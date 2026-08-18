"""Discipline module foundation tests."""

from __future__ import annotations

from datetime import date

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.accounts.services import ensure_system_roles
from apps.discipline.models import AttendanceSchedule, ClassAttendanceSheet, DailyAttendance, StudentAttendanceRecord
from apps.secretariat.models import SchoolClass
from apps.secretariat.services.academic_service import create_academic_year
from apps.secretariat.services.card_service import generate_card
from apps.secretariat.services.enrollment_service import create_enrollment
from apps.secretariat.services.student_service import create_student
from apps.secretariat.services.academic_service import create_level, create_school_class, create_section
from apps.secretariat.services.year_context import SESSION_KEY


@pytest.fixture
def roles(db):
    return ensure_system_roles()


@pytest.fixture
def discipline_user(roles):
    return User.objects.create_user(
        username="discipline1",
        password="TempPass123!",
        nom="Kanku",
        prenom="Mado",
        role=roles[Role.CODE_DISCIPLINE],
    )


@pytest.fixture
def accountant(roles):
    return User.objects.create_user(
        username="comptable-x",
        password="TempPass123!",
        nom="Kabasele",
        prenom="Paul",
        role=roles[Role.CODE_COMPTABLE],
    )


@pytest.fixture
def open_year(db):
    return create_academic_year(
        label="2026-2027",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 7, 31),
    )


@pytest.fixture
def discipline_structure(open_year, discipline_user):
    level = create_level(name="7e", code="L7")
    section = create_section(name="Secondaire", code="SEC")
    school_class = create_school_class(
        academic_year=open_year,
        level=level,
        section=section,
        name="7e A",
        code="7A",
        letter="A",
        max_capacity=60,
        actor=discipline_user,
    )
    student = create_student(
        nom="Kanku",
        prenom="Elie",
        sexe="M",
        date_naissance=date(2012, 3, 15),
        date_admission=open_year.start_date,
    )
    enrollment = create_enrollment(
        student=student,
        school_class=school_class,
        enrollment_type="NOUVELLE_INSCRIPTION",
        actor=discipline_user,
        skip_reenrollment_guard=True,
    )
    card = generate_card(enrollment=enrollment, actor=discipline_user)
    return {"class": school_class, "student": student, "enrollment": enrollment, "card": card}


def _set_year(client, year):
    session = client.session
    session[SESSION_KEY] = year.pk
    session.save()


@pytest.mark.django_db
def test_discipline_redirected_to_year_picker_without_selection(client, discipline_user):
    client.force_login(discipline_user)
    response = client.get(reverse("dashboard:home"))
    assert response.status_code == 302
    assert response.url == reverse("secretariat:academic-year-select")


@pytest.mark.django_db
def test_discipline_dashboard_requires_role(client, accountant, open_year):
    client.force_login(accountant)
    _set_year(client, open_year)
    response = client.get(reverse("discipline:dashboard"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_discipline_can_choose_year_and_open_dashboard(client, discipline_user, open_year):
    client.force_login(discipline_user)
    choose = client.post(reverse("secretariat:academic-year-choose", args=[open_year.public_id]))
    assert choose.status_code == 302
    assert choose.url == reverse("discipline:dashboard")

    response = client.get(reverse("discipline:dashboard"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Tableau de bord discipline" in body
    assert open_year.label in body


@pytest.mark.django_db
def test_discipline_qr_scan_creates_attendance(client, discipline_user, open_year, discipline_structure):
    client.force_login(discipline_user)
    _set_year(client, open_year)
    card = discipline_structure["card"]

    response = client.post(
        reverse("discipline:attendance-scan-submit"),
        data={"qr": card.qr_identifier, "operation": "arrivee"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "Arrivée enregistrée" in payload["data"]["message"] or "retard" in payload["data"]["message"].lower()
    attendance = DailyAttendance.objects.get(enrollment=discipline_structure["enrollment"], date=timezone.localdate())
    assert attendance.status in {DailyAttendance.Status.PRESENT, DailyAttendance.Status.LATE}


@pytest.mark.django_db
def test_discipline_qr_duplicate_is_flagged(client, discipline_user, open_year, discipline_structure):
    client.force_login(discipline_user)
    _set_year(client, open_year)
    card = discipline_structure["card"]
    url = reverse("discipline:attendance-scan-submit")

    first = client.post(url, data={"qr": card.qr_identifier, "operation": "arrivee"})
    assert first.status_code == 200
    second = client.post(url, data={"qr": card.qr_identifier, "operation": "arrivee"})
    assert second.status_code == 200
    payload = second.json()
    assert payload["ok"] is True
    assert payload["data"]["duplicate"] is True


@pytest.mark.django_db
def test_discipline_late_minutes_uses_schedule(client, discipline_user, open_year, discipline_structure):
    client.force_login(discipline_user)
    _set_year(client, open_year)
    school_class = discipline_structure["class"]
    AttendanceSchedule.objects.create(
        academic_year=open_year,
        school_class=school_class,
        label="Horaire standard",
        start_time=timezone.datetime(2026, 1, 1, 7, 0).time(),
        tolerance_minutes=0,
    )
    card = discipline_structure["card"]
    response = client.post(
        reverse("discipline:attendance-scan-submit"),
        data={"qr": card.qr_identifier, "operation": "arrivee"},
    )
    assert response.status_code == 200
    attendance = DailyAttendance.objects.get(enrollment=discipline_structure["enrollment"], date=timezone.localdate())
    assert attendance.late_minutes >= 0


@pytest.mark.django_db
def test_class_flow_opens_folders_and_sheet(client, discipline_user, open_year, discipline_structure):
    client.force_login(discipline_user)
    _set_year(client, open_year)
    school_class = discipline_structure["class"]
    folders_url = reverse("discipline:class-attendance-folders", kwargs={"class_id": school_class.public_id})
    folders = client.get(folders_url)
    assert folders.status_code == 200
    sheet_url = reverse(
        "discipline:class-attendance-sheet",
        kwargs={"class_id": school_class.public_id, "sheet_date": open_year.start_date.isoformat()},
    )
    sheet = client.get(sheet_url)
    assert sheet.status_code == 200
    created_sheet = ClassAttendanceSheet.objects.get(school_class=school_class, date=open_year.start_date)
    assert created_sheet.total_students >= 1


@pytest.mark.django_db
def test_sheet_draft_maps_present_and_absent(client, discipline_user, open_year, discipline_structure):
    client.force_login(discipline_user)
    _set_year(client, open_year)
    school_class = discipline_structure["class"]
    sheet_url = reverse(
        "discipline:class-attendance-sheet",
        kwargs={"class_id": school_class.public_id, "sheet_date": open_year.start_date.isoformat()},
    )
    client.get(sheet_url)
    sheet = ClassAttendanceSheet.objects.get(school_class=school_class, date=open_year.start_date)
    record = sheet.records.get(enrollment=discipline_structure["enrollment"])
    response = client.post(
        sheet_url,
        data={
            "action": "save_draft",
            f"record-status-{record.id}": StudentAttendanceRecord.Status.PRESENT,
        },
    )
    assert response.status_code == 302
    record.refresh_from_db()
    assert record.presence_value == 1
    assert record.mention == "OK"


@pytest.mark.django_db
def test_sheet_validate_marks_unmarked_as_absent(client, discipline_user, open_year, discipline_structure):
    client.force_login(discipline_user)
    _set_year(client, open_year)
    school_class = discipline_structure["class"]
    sheet_url = reverse(
        "discipline:class-attendance-sheet",
        kwargs={"class_id": school_class.public_id, "sheet_date": open_year.start_date.isoformat()},
    )
    client.get(sheet_url)
    sheet = ClassAttendanceSheet.objects.get(school_class=school_class, date=open_year.start_date)
    record = sheet.records.get(enrollment=discipline_structure["enrollment"])
    assert record.status == StudentAttendanceRecord.Status.UNMARKED

    response = client.post(sheet_url, data={"action": "validate"})
    assert response.status_code == 302
    sheet.refresh_from_db()
    record.refresh_from_db()
    assert sheet.status == ClassAttendanceSheet.Status.VALIDATED
    assert record.status == StudentAttendanceRecord.Status.ABSENT
    assert sheet.total_unmarked == 0
    assert sheet.total_absent >= 1


@pytest.mark.django_db
def test_schedule_present_late_and_reject_after_end(open_year, discipline_structure):
    from datetime import datetime, time

    from apps.discipline.services.attendance_service import _evaluate_arrival_status
    from apps.discipline.services.exceptions import DisciplineError

    school_class = discipline_structure["class"]
    school_class.vacation = SchoolClass.Vacation.MORNING
    school_class.save(update_fields=["vacation"])
    AttendanceSchedule.objects.create(
        academic_year=open_year,
        vacation=AttendanceSchedule.Vacation.MORNING,
        label="Horaire avant-midi",
        start_time=time(7, 30),
        present_until=time(7, 45),
        tolerance_minutes=15,
        end_time=time(12, 30),
    )
    enrollment = discipline_structure["enrollment"]
    tz = timezone.get_current_timezone()

    present_at = timezone.make_aware(datetime(2026, 9, 2, 7, 40), tz)
    status, minutes = _evaluate_arrival_status(enrollment, present_at)
    assert status == DailyAttendance.Status.PRESENT
    assert minutes == 0

    late_at = timezone.make_aware(datetime(2026, 9, 2, 8, 0), tz)
    status, minutes = _evaluate_arrival_status(enrollment, late_at)
    assert status == DailyAttendance.Status.LATE
    assert minutes == 15

    after_end = timezone.make_aware(datetime(2026, 9, 2, 12, 31), tz)
    with pytest.raises(DisciplineError, match="cours sont terminés"):
        _evaluate_arrival_status(enrollment, after_end)


@pytest.mark.django_db
def test_schedules_page_saves_morning_vacation(client, discipline_user, open_year, discipline_structure):
    client.force_login(discipline_user)
    _set_year(client, open_year)
    school_class = discipline_structure["class"]
    url = reverse("discipline:schedules")
    assert client.get(url).status_code == 200
    response = client.post(
        url,
        data={
            "vacation": "AVANT_MIDI",
            "AVANT_MIDI-vacation": "AVANT_MIDI",
            "AVANT_MIDI-start_time": "07:30",
            "AVANT_MIDI-present_until": "07:45",
            "AVANT_MIDI-end_time": "12:30",
            "AVANT_MIDI-school_classes": [str(school_class.pk)],
        },
    )
    assert response.status_code == 302
    schedule = AttendanceSchedule.objects.get(
        academic_year=open_year,
        vacation=AttendanceSchedule.Vacation.MORNING,
    )
    assert schedule.start_time.hour == 7
    assert schedule.present_until.minute == 45
    school_class.refresh_from_db()
    assert school_class.vacation == SchoolClass.Vacation.MORNING

