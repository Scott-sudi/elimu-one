"""Cohort-based student lifecycle for multi-year demo seeding."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from apps.secretariat.models import (
    AcademicYear,
    Enrollment,
    Guardian,
    Option,
    SchoolClass,
    SchoolLevel,
    Section,
    Student,
    StudentGuardian,
)
from apps.secretariat.services.guardian_identification_service import (
    next_guardian_identification,
)

LEVEL_ORDER = ("7E", "8E", "1E", "2E", "3E", "4E")
LEVEL_NEXT = {"7E": "8E", "8E": "1E", "1E": "2E", "2E": "3E", "3E": "4E", "4E": None}
OPTION_CODES = ("SCIENCE", "PG", "CG", "MECA", "ELEC")


@dataclass
class CohortMember:
    student: Student
    guardian: Guardian
    level_code: str
    option_code: str | None = None


@dataclass
class CohortState:
    members: list[CohortMember] = field(default_factory=list)
    used_phones: set[str] = field(default_factory=set)
    guardian_seq: int = 0
    student_seq: int = 0
    sibling_pool: list[Guardian] = field(default_factory=list)


def _pick_option(rng: random.Random) -> str:
    weights = [3.0, 2.5, 2.0, 1.2, 1.0]
    return rng.choices(list(OPTION_CODES), weights=weights, k=1)[0]


def _class_for_member(
    *,
    classes: list[SchoolClass],
    level_code: str,
    option_code: str | None,
    rng: random.Random,
) -> SchoolClass:
    candidates = [
        c
        for c in classes
        if c.level.code == level_code
        and (level_code in {"7E", "8E"} or (c.option and c.option.code == option_code))
    ]
    if not candidates:
        return rng.choice(classes)
    return rng.choice(candidates)


def _assign_slots_to_classes(
    *,
    count: int,
    classes: list[SchoolClass],
    rng: random.Random,
) -> list[SchoolClass]:
    if not classes or count <= 0:
        return []
    weights = []
    for klass in classes:
        base = 1.0
        if klass.level.code in {"7E", "8E"}:
            base = rng.uniform(2.2, 3.8)
        elif klass.level.code in {"1E", "2E"}:
            base = rng.uniform(1.4, 2.6)
        else:
            base = rng.uniform(0.8, 1.8)
        weights.append(base * rng.uniform(0.55, 1.45))

    slots: list[SchoolClass] = []
    remaining = count
    raw = [w / sum(weights) * count for w in weights]
    floors = [int(x) for x in raw]
    for i, n in enumerate(floors):
        slots.extend([classes[i]] * n)
        remaining -= n
    order = sorted(range(len(classes)), key=lambda i: weights[i], reverse=True)
    idx = 0
    while remaining > 0 and order:
        slots.append(classes[order[idx % len(order)]])
        remaining -= 1
        idx += 1
    rng.shuffle(slots)
    return slots[:count]


def create_guardian_for_seed(
    *,
    rng: random.Random,
    state: CohortState,
    nom: str,
    postnom: str,
    prenom: str,
    sexe: str,
    adresse: str,
    year_start: int,
    school_class: SchoolClass | None,
    noms: tuple[str, ...],
    postnoms: tuple[str, ...],
    prenoms_m: tuple[str, ...],
    prenoms_f: tuple[str, ...],
    professions: tuple[str, ...],
) -> Guardian:
    for _ in range(40):
        phone = f"+243{rng.choice((81, 82, 84, 85, 97, 99))}{rng.randint(1000000, 9999999)}"
        digits = phone.replace("+243", "")
        if digits not in state.used_phones:
            state.used_phones.add(digits)
            break
    else:
        phone = f"+243{rng.randint(810000000, 999999999)}"

    state.guardian_seq += 1
    section_code = ""
    option_code = ""
    letter = "A"
    if school_class is not None:
        letter = school_class.letter or "A"
        if school_class.section:
            section_code = school_class.section.code
        if school_class.option:
            option_code = school_class.option.code

    ident = next_guardian_identification(
        academic_year_start=year_start,
        section_code=section_code,
        option_code=option_code,
        class_letter=letter,
        sequence=state.guardian_seq,
    )
    guardian = Guardian.objects.create(
        nom=nom if nom else rng.choice(noms),
        postnom=postnom,
        prenom=prenom,
        sexe=sexe,
        telephone_principal=phone,
        telephone_secondaire=(
            f"+243{rng.choice((81, 97))}{rng.randint(1000000, 9999999)}"
            if rng.random() < 0.28
            else ""
        ),
        email=(
            f"{prenom.lower()}.{nom.lower().replace(' ', '')}{rng.randint(1, 99)}@gmail.com"
            if rng.random() < 0.35
            else ""
        ),
        adresse=adresse,
        profession=rng.choice(professions),
        numero_identification=ident,
        is_active=True,
    )
    return guardian


def bootstrap_cohort(
    *,
    rng: random.Random,
    state: CohortState,
    year: AcademicYear,
    classes: list[SchoolClass],
    count: int,
    foreign_count: int,
    create_student_fn,
    noms,
    postnoms,
    prenoms_m,
    prenoms_f,
    lieux,
    quartiers,
    etablissements,
    foreign,
    blood,
    professions,
) -> list[Student]:
    """First year: spread students across all levels (school already running)."""
    level_buckets: dict[str, list[SchoolClass]] = {}
    for klass in classes:
        level_buckets.setdefault(klass.level.code, []).append(klass)

    distribution = {
        "7E": int(count * rng.uniform(0.22, 0.30)),
        "8E": int(count * rng.uniform(0.18, 0.24)),
        "1E": int(count * rng.uniform(0.14, 0.18)),
        "2E": int(count * rng.uniform(0.12, 0.16)),
        "3E": int(count * rng.uniform(0.08, 0.12)),
        "4E": int(count * rng.uniform(0.06, 0.10)),
    }
    while sum(distribution.values()) < count:
        distribution[rng.choice(list(distribution.keys()))] += 1
    while sum(distribution.values()) > count:
        key = max(distribution, key=distribution.get)
        if distribution[key] > 1:
            distribution[key] -= 1

    created: list[Student] = []
    foreign_left = foreign_count
    for level_code, level_count in distribution.items():
        level_classes = level_buckets.get(level_code, [])
        if not level_classes:
            continue
        slots = _assign_slots_to_classes(count=level_count, classes=level_classes, rng=rng)
        for klass in slots:
            is_foreign = foreign_left > 0 and rng.random() < 0.35
            if is_foreign:
                foreign_left -= 1
            option_code = klass.option.code if klass.option else None
            student, guardian = create_student_fn(
                rng=rng,
                klass=klass,
                year=year,
                is_foreign=is_foreign,
                option_code=option_code,
                state=state,
            )
            created.append(student)
            state.members.append(
                CohortMember(
                    student=student,
                    guardian=guardian,
                    level_code=level_code,
                    option_code=option_code,
                )
            )
    return created


def advance_cohort(
    *,
    rng: random.Random,
    state: CohortState,
    year: AcademicYear,
    classes: list[SchoolClass],
    target_count: int,
    foreign_count: int,
    create_student_fn,
) -> list[Student]:
    """Promote / repeat / graduate, then add new 7E entrants."""
    next_members: list[CohortMember] = []
    for member in state.members:
        if member.level_code == "4E" and rng.random() < 0.88:
            continue
        fail_rate = 0.06 + (0.04 if member.level_code in {"3E", "4E"} else 0.0)
        if rng.random() < fail_rate:
            next_level = member.level_code
            next_option = member.option_code
        else:
            next_level = LEVEL_NEXT[member.level_code] or member.level_code
            if member.level_code == "8E":
                next_option = _pick_option(rng)
            elif next_level in {"7E", "8E"}:
                next_option = None
            else:
                next_option = member.option_code or _pick_option(rng)
        if next_level == member.level_code and member.level_code == "4E":
            continue
        next_members.append(
            CohortMember(
                student=member.student,
                guardian=member.guardian,
                level_code=next_level,
                option_code=next_option,
            )
        )

    enrolled_students: list[Student] = []
    by_level: dict[str, list[CohortMember]] = {}
    for member in next_members:
        by_level.setdefault(member.level_code, []).append(member)

    for level_code, members in by_level.items():
        level_classes = [
            c
            for c in classes
            if c.level.code == level_code
            and (level_code in {"7E", "8E"} or not members[0].option_code or c.option.code == members[0].option_code)
        ]
        if not level_classes:
            level_classes = [c for c in classes if c.level.code == level_code] or classes
        rng.shuffle(members)
        slots = _assign_slots_to_classes(count=len(members), classes=level_classes, rng=rng)
        for member, klass in zip(members, slots, strict=False):
            enrollment = enroll_existing_member(
                member=member,
                klass=klass,
                year=year,
                rng=rng,
            )
            member.student._seed_enrollment = enrollment  # type: ignore[attr-defined]
            enrolled_students.append(member.student)

    current_total = len(next_members)
    newcomers = max(0, target_count - current_total)
    seven_classes = [c for c in classes if c.level.code == "7E"]
    if newcomers and seven_classes:
        slots = _assign_slots_to_classes(count=newcomers, classes=seven_classes, rng=rng)
        foreign_left = foreign_count
        for klass in slots:
            is_foreign = foreign_left > 0 and rng.random() < 0.4
            if is_foreign:
                foreign_left -= 1
            student, guardian = create_student_fn(
                rng=rng,
                klass=klass,
                year=year,
                is_foreign=is_foreign,
                option_code=None,
                state=state,
            )
            enrolled_students.append(student)
            next_members.append(
                CohortMember(
                    student=student,
                    guardian=guardian,
                    level_code="7E",
                    option_code=None,
                )
            )

    state.members = next_members
    return enrolled_students


def enroll_existing_member(
    *,
    member: CohortMember,
    klass: SchoolClass,
    year: AcademicYear,
    rng: random.Random,
) -> Enrollment:
    previous = (
        Enrollment.objects.filter(student=member.student, academic_year__start_date__lt=year.start_date)
        .order_by("-academic_year__start_date")
        .first()
    )
    enrollment_type = (
        Enrollment.EnrollmentType.RENEWAL
        if previous
        else Enrollment.EnrollmentType.NEW
    )
    if previous and member.level_code == previous.school_class.level.code:
        enrollment_type = Enrollment.EnrollmentType.RENEWAL
    elif previous and member.level_code != previous.school_class.level.code:
        enrollment_type = Enrollment.EnrollmentType.RENEWAL
    return Enrollment.objects.create(
        student=member.student,
        academic_year=year,
        school_class=klass,
        enrollment_number=f"INS{year.start_date.year}{member.student.pk:05d}",
        enrollment_type=enrollment_type,
        enrollment_date=year.start_date + timedelta(days=rng.randint(0, 25)),
        status=Enrollment.Status.VALIDATED,
        provenance=member.student.ancien_etablissement,
    )


def build_student_factory(
    *,
    actor,
    noms: tuple[str, ...],
    postnoms: tuple[str, ...],
    prenoms_m: tuple[str, ...],
    prenoms_f: tuple[str, ...],
    lieux: tuple[str, ...],
    quartiers: tuple[str, ...],
    etablissements: tuple[str, ...],
    foreign: tuple[tuple[str, str, str], ...],
    blood: tuple[str, ...],
    professions: tuple[str, ...],
):
    """Return a cohort-compatible factory that creates students + guardians."""

    def factory(*, rng, klass, year, is_foreign, option_code, state: CohortState):
        state.student_seq += 1
        sexe = rng.choice([Student.Gender.MALE, Student.Gender.FEMALE])
        prenom = rng.choice(prenoms_m if sexe == Student.Gender.MALE else prenoms_f)

        if is_foreign:
            nationalite, lieu_a, lieu_b = rng.choice(foreign)
            lieu = rng.choice([lieu_a, lieu_b])
            nom = rng.choice(
                ("Banda", "Phiri", "Mwale", "Tembo", "Chirwa", "Okello", "Nkurunziza", "Uwamahoro")
            )
            postnom = ""
            adresse = f"Avenue Frontière, {rng.choice(quartiers)}, Likasi"
        else:
            nationalite = "Congolaise"
            lieu = rng.choice(lieux)
            nom = rng.choice(noms)
            postnom = rng.choice(postnoms)
            adresse = (
                f"Avenue {rng.choice(('Lumumba', 'Mobutu', 'Kasavubu', 'Sendwe', 'Likasi'))} "
                f"n°{rng.randint(1, 240)}, {rng.choice(quartiers)}, Likasi"
            )

        age = {
            "7E": rng.randint(12, 14),
            "8E": rng.randint(13, 15),
            "1E": rng.randint(14, 16),
            "2E": rng.randint(15, 17),
            "3E": rng.randint(16, 18),
            "4E": rng.randint(17, 20),
        }[klass.level.code]
        birth = date(
            year.start_date.year - age,
            rng.randint(1, 12),
            rng.randint(1, 28),
        )
        admission_base = year.start_date - timedelta(days=20)
        matricule = f"KAL{year.start_date.year}{state.student_seq:05d}"

        student = Student.objects.create(
            matricule=matricule,
            nom=nom,
            postnom=postnom,
            prenom=prenom,
            sexe=sexe,
            date_naissance=birth,
            lieu_naissance=lieu,
            nationalite=nationalite,
            adresse=adresse,
            ancien_etablissement=rng.choice(etablissements) if rng.random() < 0.45 else "",
            date_admission=admission_base + timedelta(days=rng.randint(0, 40)),
            statut=Student.Status.ACTIVE,
            is_active=True,
            is_archived=False,
            groupe_sanguin=rng.choice(blood) if rng.random() < 0.7 else "",
            allergies="Arachides" if rng.random() < 0.04 else "",
            observations="",
        )

        if state.sibling_pool and rng.random() < 0.16:
            guardian = rng.choice(state.sibling_pool)
        else:
            g_sexe = rng.choice([Guardian.Gender.MALE, Guardian.Gender.FEMALE])
            g_prenom = rng.choice(prenoms_m if g_sexe == Guardian.Gender.MALE else prenoms_f)
            guardian = create_guardian_for_seed(
                rng=rng,
                state=state,
                nom=nom if not is_foreign and rng.random() < 0.55 else rng.choice(noms),
                postnom=rng.choice(postnoms) if not is_foreign else "",
                prenom=g_prenom,
                sexe=g_sexe,
                adresse=adresse,
                year_start=year.start_date.year,
                school_class=klass,
                noms=noms,
                postnoms=postnoms,
                prenoms_m=prenoms_m,
                prenoms_f=prenoms_f,
                professions=professions,
            )
            state.sibling_pool.append(guardian)

        if guardian.sexe == Guardian.Gender.MALE:
            lien = rng.choice(
                [
                    StudentGuardian.Relationship.FATHER,
                    StudentGuardian.Relationship.FATHER,
                    StudentGuardian.Relationship.UNCLE,
                    StudentGuardian.Relationship.LEGAL_GUARDIAN,
                ]
            )
        elif guardian.sexe == Guardian.Gender.FEMALE:
            lien = rng.choice(
                [
                    StudentGuardian.Relationship.MOTHER,
                    StudentGuardian.Relationship.MOTHER,
                    StudentGuardian.Relationship.AUNT,
                    StudentGuardian.Relationship.LEGAL_GUARDIAN,
                ]
            )
        else:
            lien = StudentGuardian.Relationship.LEGAL_GUARDIAN

        StudentGuardian.objects.create(
            student=student,
            guardian=guardian,
            lien_parente=lien,
            is_primary=True,
            is_emergency_contact=True,
            can_pickup=True,
            receives_notifications=True,
            lives_with_student=rng.random() < 0.85,
        )

        enrollment = Enrollment.objects.create(
            student=student,
            academic_year=year,
            school_class=klass,
            enrollment_number=f"INS{year.start_date.year}{state.student_seq:05d}",
            enrollment_type=Enrollment.EnrollmentType.NEW,
            enrollment_date=student.date_admission,
            status=Enrollment.Status.VALIDATED,
            provenance=student.ancien_etablissement,
            created_by=actor,
        )
        student._seed_enrollment = enrollment  # type: ignore[attr-defined]
        return student, guardian

    return factory
