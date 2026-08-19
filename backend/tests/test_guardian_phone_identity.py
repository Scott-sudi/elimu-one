"""Guardian phone-identity and enrollment linking tests."""

from __future__ import annotations

from datetime import date

import pytest

from apps.secretariat.models import Student, StudentGuardian
from apps.secretariat.services.academic_service import (
    create_academic_year,
    create_level,
    create_school_class,
    create_section,
)
from apps.secretariat.services.exceptions import SecretariatError
from apps.secretariat.services.guardian_service import (
    create_guardian,
    link_responsable_to_student,
    resolve_or_create_guardian_for_enrollment,
)
from apps.secretariat.services.student_service import create_student


@pytest.fixture
def two_students(db):
    year = create_academic_year(
        label="2027-2028-G",
        start_date=date(2027, 9, 1),
        end_date=date(2028, 7, 31),
        is_active=True,
    )
    level = create_level(name="1re G", code="1G-X", order=1)
    section = create_section(name="Générale G", code="GEN-G")
    create_school_class(
        academic_year=year,
        level=level,
        section=section,
        letter="A",
        name="1re G A",
        code="1GA-27",
        max_capacity=40,
    )
    s1 = create_student(
        nom="Kabongo",
        prenom="Alice",
        sexe=Student.Gender.FEMALE,
        date_naissance=date(2012, 1, 1),
        date_admission=date(2027, 9, 1),
    )
    s2 = create_student(
        nom="Kabongo",
        prenom="Bob",
        sexe=Student.Gender.MALE,
        date_naissance=date(2014, 2, 2),
        date_admission=date(2027, 9, 1),
    )
    return {"s1": s1, "s2": s2}


@pytest.mark.django_db
def test_same_phone_links_multiple_children(two_students):
    link1 = link_responsable_to_student(
        student=two_students["s1"],
        full_name="Jean Magiskil",
        telephone_principal="0991112233",
        lien_parente=StudentGuardian.Relationship.FATHER,
    )
    link2 = link_responsable_to_student(
        student=two_students["s2"],
        full_name="Jean",
        telephone_principal="0991112233",
        lien_parente=StudentGuardian.Relationship.FATHER,
    )
    assert link1.guardian_id == link2.guardian_id
    assert link1.guardian.student_links.count() == 2


@pytest.mark.django_db
def test_same_phone_rejects_totally_different_name(two_students):
    link_responsable_to_student(
        student=two_students["s1"],
        full_name="Jean Magiskil",
        telephone_principal="0992223344",
        lien_parente=StudentGuardian.Relationship.FATHER,
    )
    with pytest.raises(SecretariatError, match="nom totalement différent"):
        link_responsable_to_student(
            student=two_students["s2"],
            full_name="Pierre Autre",
            telephone_principal="0992223344",
            lien_parente=StudentGuardian.Relationship.UNCLE,
        )


@pytest.mark.django_db
def test_compatible_partial_name_and_enrichment(two_students):
    first = resolve_or_create_guardian_for_enrollment(
        full_name="Jean",
        telephone_principal="0993334455",
    )
    assert first.nom == "Jean"
    second = resolve_or_create_guardian_for_enrollment(
        full_name="Jean Magiskil Miniskil",
        telephone_principal="0993334455",
    )
    assert second.pk == first.pk
    second.refresh_from_db()
    full = f"{second.nom} {second.postnom} {second.prenom}".lower()
    assert "jean" in full
    assert "magiskil" in full
    assert "miniskil" in full


@pytest.mark.django_db
def test_create_guardian_blocks_duplicate_phone():
    create_guardian(nom="Ilunga", prenom="Jean", telephone_principal="0810000001")
    with pytest.raises(SecretariatError, match="déjà lié"):
        create_guardian(nom="Autre", prenom="Nom", telephone_principal="0810000001")


@pytest.mark.django_db
def test_local_zero_and_plus243_are_same_phone(two_students):
    link1 = link_responsable_to_student(
        student=two_students["s1"],
        full_name="Jean Magiskil",
        telephone_principal="0812345678",
        lien_parente=StudentGuardian.Relationship.FATHER,
    )
    link2 = link_responsable_to_student(
        student=two_students["s2"],
        full_name="Jean",
        telephone_principal="+243812345678",
        lien_parente=StudentGuardian.Relationship.FATHER,
    )
    assert link1.guardian_id == link2.guardian_id

    with pytest.raises(SecretariatError, match="déjà lié"):
        create_guardian(
            nom="Autre",
            prenom="Personne",
            telephone_principal="+243812345678",
        )


@pytest.mark.django_db
def test_bare_243_without_plus_is_normalized():
    guardian = create_guardian(
        nom="Ilunga",
        prenom="Jean",
        telephone_principal="243812345678",
    )
    assert guardian.telephone_principal == "+243812345678"


@pytest.mark.django_db
def test_student_cannot_have_two_guardians(two_students):
    from apps.secretariat.services.exceptions import SecretariatError
    from apps.secretariat.services.guardian_service import associate_guardian, create_guardian

    guardian_a = create_guardian(nom="Ilunga", prenom="Jean", telephone_principal="0811000001")
    guardian_b = create_guardian(nom="Kabongo", prenom="Marie", telephone_principal="0811000002")
    associate_guardian(
        student=two_students["s1"],
        guardian=guardian_a,
        lien_parente=StudentGuardian.Relationship.FATHER,
    )
    with pytest.raises(SecretariatError, match="qu'un seul responsable"):
        associate_guardian(
            student=two_students["s1"],
            guardian=guardian_b,
            lien_parente=StudentGuardian.Relationship.MOTHER,
        )


@pytest.mark.django_db
def test_new_guardian_gets_kal_parent_id(two_students):
    link = link_responsable_to_student(
        student=two_students["s1"],
        full_name="Marie Parent",
        telephone_principal="0998887766",
        lien_parente=StudentGuardian.Relationship.MOTHER,
        academic_year_start=2027,
    )
    assert link.guardian.numero_identification.startswith("ELM2027R")


@pytest.mark.django_db
def test_create_guardian_ignores_manual_identification():
    guardian = create_guardian(
        nom="Mwamba",
        prenom="Paul",
        telephone_principal="0995556677",
        numero_identification="SAISIE-MANUELLE",
        academic_year_start=2027,
    )
    assert guardian.numero_identification.startswith("ELM2027R")
    assert guardian.numero_identification != "SAISIE-MANUELLE"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0812345678", "812345678"),
        ("+243812345678", "812345678"),
        ("+243 812 345 678", "812345678"),
    ],
)
def test_normalize_phone_drc_variants(raw, expected):
    from apps.secretariat.services.guardian_service import normalize_phone

    assert normalize_phone(raw) == expected
