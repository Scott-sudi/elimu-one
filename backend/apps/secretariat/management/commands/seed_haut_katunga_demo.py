"""Seed realistic Haut-Katanga (RDC) demo data for the secretariat module.

Creates school years 2009-2010 → 2026-2027 with organisation, classes,
cohort-based students, enrollments, documents, communications and cards.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.secretariat.models import (
    AcademicYear,
    ClassTransfer,
    Communication,
    CommunicationReceipt,
    CommunicationTarget,
    DocumentType,
    Enrollment,
    Guardian,
    Option,
    SchoolClass,
    SchoolLevel,
    Section,
    Student,
    StudentCard,
    StudentDocument,
    StudentGuardian,
)
from apps.secretariat.seed.demo_cohort import (
    CohortState,
    advance_cohort,
    bootstrap_cohort,
    build_student_factory,
)

# ---------------------------------------------------------------------------
# Reference data — structure réelle de l'Institut Kalunga (Likasi, code 71041)
# ---------------------------------------------------------------------------

LEVELS = (
    ("7ème année", "7E", 1, "Enseignement de base — 7ème année"),
    ("8ème année", "8E", 2, "Enseignement de base — 8ème année"),
    ("1ère année", "1E", 3, "Première année des humanités / techniques"),
    ("2ème année", "2E", 4, "Deuxième année des humanités / techniques"),
    ("3ème année", "3E", 5, "Troisième année des humanités / techniques"),
    ("4ème année", "4E", 6, "Quatrième année (terminale)"),
)

SECTIONS = (
    ("Scientifique", "SCI", "Section scientifique — option Science"),
    ("Pédagogie générale", "PED", "Section pédagogie générale"),
    ("Commerciale & gestion", "COM", "Section commerciale et gestion"),
    ("Mécanique générale", "MG", "Section mécanique générale"),
    ("Electricité", "EL", "Section électricité"),
)

OPTIONS = (
    ("SCI", "Science", "SCIENCE", "Option Science"),
    ("PED", "Pédagogie générale", "PG", "Option Pédagogie générale"),
    ("COM", "Commerciale & gestion", "CG", "Option Commerciale & gestion"),
    ("MG", "Mécanique générale", "MECA", "Option Mécanique générale"),
    ("EL", "Electricité", "ELEC", "Option Electricité"),
)

# Années scolaires : 2009-2010 … 2026-2027 (2026-2027 = année en cours)
SCHOOL_YEARS = tuple(
    {
        "label": f"{start}-{start + 1}",
        "start_date": date(start, 9, 1),
        "end_date": date(start + 1, 7, 15),
    }
    for start in range(2009, 2027)
)

ACTIVE_YEAR_LABEL = "2026-2027"

NOMS = (
    "Mutombo", "Kabongo", "Mwamba", "Ilunga", "Kalala", "Kasongo", "Tshibanda",
    "Mbuyu", "Nkulu", "Kyungu", "Kapend", "Ngoy", "Mulongo", "Kajemba",
    "Kazadi", "Mwanza", "Banza", "Kitenge", "Mukeba", "Sumbu", "Lwamba",
    "Katanga", "Mumba", "Ngoie", "Kabeya", "Muyumba", "Kalenga", "Musonda",
    "Chomba", "Kapapa", "Lubamba", "Mukendi", "Tumba", "Kanyama", "Mbuya",
    "Kabwe", "Nday", "Shabani", "Mputu", "Kalonji", "Lumbala", "Mwenze",
)

POSTNOMS = (
    "Wa Ilunga", "Wa Kabongo", "Dit Mutombo", "Dit Kalala", "Wa Mwamba",
    "Kanyama", "Mukeba", "Kasongo", "Tshibanda", "Mbuyu", "Nkulu", "Kyungu",
    "Kapend", "Ngoy", "Mulongo", "Kajemba", "Kazadi", "Mwanza", "Banza",
    "Kitenge", "Sumbu", "Lwamba", "Mumba", "Ngoie", "Kabeya", "Muyumba",
    "Kalenga", "Musonda", "Chomba", "Lubamba", "Mukendi", "Tumba", "Mbuya",
    "Kabwe", "Shabani", "Mputu", "Kalonji", "Lumbala", "Mwenze", "Dit Sudi",
)

PRENOMS_M = (
    "Jean", "Patrick", "Jonathan", "Divine", "Joseph", "Eric", "David",
    "Christian", "Serge", "Alain", "Bienvenu", "Patient", "Trésor", "Héritier",
    "Espoir", "Gédéon", "Isaac", "Moïse", "Samuel", "Daniel", "Pierre",
    "André", "Paul", "Jacques", "Emmanuel", "Josué", "Caleb", "Nathan",
)

PRENOMS_F = (
    "Marie", "Grace", "Esther", "Divine", "Deborah", "Sarah", "Ruth",
    "Patience", "Bénie", "Dorcas", "Rachel", "Léa", "Naomi", "Joëlle",
    "Carine", "Ornella", "Prisca", "Chancelle", "Espérance", "Victoire",
    "Aimée", "Solange", "Thérèse", "Christine", "Judith", "Rebecca",
)

LIEUX_NAISSANCE = (
    "Likasi", "Lubumbashi", "Kipushi", "Kambove", "Fungurume", "Kolwezi",
    "Kasumbalesa", "Sakania", "Pweto", "Mitwaba", "Manono", "Kamina",
    "Kinshasa", "Kananga", "Mbuji-Mayi", "Bukavu", "Goma", "Kisangani",
)

QUARTIERS_LIKASI = (
    "Centre-ville", "Panda", "Kikula", "Shituru", "Gécamines",
    "SNCC", "Kampemba", "Golf", "Kakanda", "Kamatanda",
)

PROFESSIONS = (
    "Commerçant(e)", "Enseignant(e)", "Infirmier(ère)", "Chauffeur",
    "Agent de sécurité", "Fonctionnaire", "Mineur", "Mécanicien",
    "Couturière", "Coiffeur(se)", "Agriculteur(trice)", "Comptable",
    "Médecin", "Pasteur", "Électricien", "Menuisier", "Vendeur(se)",
    "Agent Gécamines", "Agent TFM", "Agent Kamoa", "Sans emploi",
)

ETABLISSEMENTS = (
    "Institut Technique de Lubumbashi", "Collège Saint François-Xavier",
    "Institut Pédagogique de Likasi", "Lycée Anuarite", "Collège Imara",
    "Institut Technique Kolwezi", "École Secondaire de Kipushi",
    "Collège Notre-Dame de Lourdes", "Institut Mwanga", "École Communautaire Ruashi",
)

FOREIGN = (
    ("Zambienne", "Kitwe", "Ndola"),
    ("Zambienne", "Lusaka", "Chingola"),
    ("Angolaise", "Luanda", "Benguela"),
    ("Tanzanienne", "Dar es Salaam", "Mbeya"),
    ("Rwandaise", "Kigali", "Butare"),
    ("Burundaise", "Bujumbura", "Gitega"),
    ("Malawienne", "Lilongwe", "Blantyre"),
    ("Sud-africaine", "Johannesburg", "Pretoria"),
)

BLOOD = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")


def _students_for_year(label: str, rng: random.Random) -> int:
    """Varied headcount per year — never a flat identical figure."""
    start = int(label.split("-")[0])
    # Independent jitter so neighbouring years rarely match.
    jitter = rng.randint(-18, 27)
    if start >= 2025:
        base = rng.randint(168, 255)
    elif start >= 2023:
        base = rng.randint(140, 210)
    elif start >= 2021:
        base = rng.randint(118, 185)
    elif start >= 2019:
        base = rng.randint(95, 165)
    elif start >= 2017:
        base = rng.randint(78, 145)
    else:
        base = rng.randint(58, 120)
    return max(40, base + jitter)


class Command(BaseCommand):
    help = (
        "Remplace les données secrétariat par des années scolaires 2009-2027 "
        "peuplées pour l'Institut Kalunga (cohortes réalistes)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--students",
            type=int,
            default=220,
            help="Effectif cible pour les années récentes (défaut: 220).",
        )
        parser.add_argument(
            "--foreign",
            type=int,
            default=6,
            help="Élèves étrangers par année récente (défaut: 6).",
        )
        parser.add_argument(
            "--skip-cards",
            action="store_true",
            help="Ne pas générer les cartes PNG/PDF (plus rapide).",
        )
        parser.add_argument(
            "--skip-discipline",
            action="store_true",
            help="Ne pas lancer seed_discipline_demo après le seed principal.",
        )
        parser.add_argument(
            "--skip-finance",
            action="store_true",
            help="Ne pas lancer seed_finance_payments après le seed principal.",
        )
        parser.add_argument(
            "--cards-from",
            type=str,
            default="2022-2023",
            help="Générer les cartes à partir de cette année inclusive (défaut: 2022-2023).",
        )

    def handle(self, *args, **options):
        base_students = options["students"]
        foreign_base = options["foreign"]
        skip_cards = options["skip_cards"]
        skip_discipline = options["skip_discipline"]
        skip_finance = options["skip_finance"]
        cards_from = options["cards_from"]
        rng = random.Random(20260722)

        card_jobs: list[tuple[AcademicYear, list[Student]]] = []
        cohort_state = CohortState()

        with transaction.atomic():
            self.stdout.write("Nettoyage des données secrétariat existantes…")
            self._purge()

            self.stdout.write("Création de l'organisation (niveaux, sections, options)…")
            levels = self._create_levels()
            sections = self._create_sections()
            options_map = self._create_options(sections)

            self.stdout.write(f"Création des {len(SCHOOL_YEARS)} années scolaires…")
            years = self._create_years()

            actor = User.objects.filter(is_archived=False).order_by("id").first()

            student_factory = build_student_factory(
                actor=actor,
                noms=NOMS,
                postnoms=POSTNOMS,
                prenoms_m=PRENOMS_M,
                prenoms_f=PRENOMS_F,
                lieux=LIEUX_NAISSANCE,
                quartiers=QUARTIERS_LIKASI,
                etablissements=ETABLISSEMENTS,
                foreign=FOREIGN,
                blood=BLOOD,
                professions=PROFESSIONS,
            )

            for year_index, year in enumerate(years):
                year_rng = random.Random(f"{rng.random()}-{year.label}")
                count = _students_for_year(year.label, year_rng)
                foreign_count = max(1, min(foreign_base, max(2, count // year_rng.randint(22, 38))))

                self.stdout.write(f"  - {year.label} : {count} élèves…")
                classes = self._create_classes(year, levels, sections, options_map, year_rng)

                if year_index == 0:
                    students = bootstrap_cohort(
                        rng=year_rng,
                        state=cohort_state,
                        year=year,
                        classes=classes,
                        count=count,
                        foreign_count=foreign_count,
                        create_student_fn=student_factory,
                        noms=NOMS,
                        postnoms=POSTNOMS,
                        prenoms_m=PRENOMS_M,
                        prenoms_f=PRENOMS_F,
                        lieux=LIEUX_NAISSANCE,
                        quartiers=QUARTIERS_LIKASI,
                        etablissements=ETABLISSEMENTS,
                        foreign=FOREIGN,
                        blood=BLOOD,
                        professions=PROFESSIONS,
                    )
                else:
                    students = advance_cohort(
                        rng=year_rng,
                        state=cohort_state,
                        year=year,
                        classes=classes,
                        target_count=count,
                        foreign_count=foreign_count,
                        create_student_fn=student_factory,
                    )

                self._create_documents(year_rng, students, actor)
                self._create_communications(year, levels, sections, classes, actor, year_rng)

                if not skip_cards and year.label >= cards_from:
                    card_jobs.append((year, students))

        if card_jobs:
            total = sum(len(s) for _, s in card_jobs)
            self.stdout.write(
                f"Génération des cartes élèves ({total} cartes, années ≥ {cards_from})…"
            )
            done = 0
            for year, students in card_jobs:
                self.stdout.write(f"  - Cartes {year.label}…")
                self._create_cards(students, actor)
                done += len(students)
                self.stdout.write(f"     {done}/{total}")
        elif skip_cards:
            self.stdout.write("Cartes ignorées (--skip-cards).")

        if not skip_discipline:
            self.stdout.write("Peuplement discipline (présences, incidents, convocations)…")
            from django.core.management import call_command

            call_command("seed_discipline_demo", years=8, days_per_year=16)

        if not skip_finance:
            self.stdout.write("Peuplement finance (minerval année ouverte)…")
            from django.core.management import call_command

            try:
                call_command("seed_finance_payments")
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(f"Finance seed ignoré: {exc}")

        self.stdout.write(self.style.SUCCESS(self._summary(years)))

    # ------------------------------------------------------------------ purge
    def _purge(self) -> None:
        CommunicationReceipt.objects.all().delete()
        CommunicationTarget.objects.all().delete()
        Communication.objects.all().delete()
        StudentDocument.objects.all().delete()
        StudentCard.objects.all().delete()
        ClassTransfer.objects.all().delete()
        Enrollment.objects.all().delete()
        StudentGuardian.objects.all().delete()
        Student.objects.all().delete()
        Guardian.objects.all().delete()
        SchoolClass.objects.all().delete()
        Option.objects.all().delete()
        Section.objects.all().delete()
        SchoolLevel.objects.all().delete()
        AcademicYear.objects.all().delete()

    # -------------------------------------------------------------- structure
    def _create_years(self) -> list[AcademicYear]:
        years: list[AcademicYear] = []
        for spec in SCHOOL_YEARS:
            label = spec["label"]
            is_active = label == ACTIVE_YEAR_LABEL
            year = AcademicYear.objects.create(
                label=label,
                start_date=spec["start_date"],
                end_date=spec["end_date"],
                is_active=is_active,
                is_closed=not is_active,
            )
            years.append(year)
        return years

    def _create_levels(self) -> dict[str, SchoolLevel]:
        levels = {}
        for name, code, order, description in LEVELS:
            levels[code] = SchoolLevel.objects.create(
                name=name,
                code=code,
                order=order,
                description=description,
                is_active=True,
            )
        return levels

    def _create_sections(self) -> dict[str, Section]:
        sections = {}
        for name, code, description in SECTIONS:
            sections[code] = Section.objects.create(
                name=name,
                code=code,
                description=description,
                is_active=True,
            )
        return sections

    def _create_options(self, sections: dict[str, Section]) -> dict[str, Option]:
        options = {}
        for section_code, name, code, description in OPTIONS:
            options[code] = Option.objects.create(
                name=name,
                code=code,
                section=sections[section_code],
                description=description,
                is_active=True,
            )
        return options

    def _create_classes(
        self,
        year: AcademicYear,
        levels: dict[str, SchoolLevel],
        sections: dict[str, Section],
        options: dict[str, Option],
        rng: random.Random,
    ) -> list[SchoolClass]:
        created: list[SchoolClass] = []
        rooms = [f"Salle {n}" for n in range(1, 40)]
        room_i = 0

        def room() -> str:
            nonlocal room_i
            value = rooms[room_i % len(rooms)]
            room_i += 1
            return value

        for level_code, letters in (("7E", "ABC"), ("8E", "ABC")):
            for letter in letters:
                name = f"{levels[level_code].name.split()[0]} {letter}"
                created.append(
                    SchoolClass.objects.create(
                        academic_year=year,
                        level=levels[level_code],
                        section=None,
                        option=None,
                        letter=letter,
                        name=name,
                        code=f"{level_code}-{letter}",
                        max_capacity=rng.randint(42, 55),
                        room=room(),
                        is_active=True,
                    )
                )

        popular = {"SCIENCE", "CG", "PG", "ELEC", "MECA"}
        for level_code in ("1E", "2E", "3E", "4E"):
            level = levels[level_code]
            short = level.name.split()[0]
            for opt_code, option in options.items():
                letters = "AB" if opt_code in popular else "A"
                for letter in letters:
                    name = f"{short} {option.name} {letter}"
                    created.append(
                        SchoolClass.objects.create(
                            academic_year=year,
                            level=level,
                            section=option.section,
                            option=option,
                            letter=letter,
                            name=name,
                            code=f"{level_code}-{opt_code}-{letter}",
                            max_capacity=rng.randint(35, 48),
                            room=room(),
                            is_active=True,
                        )
                    )
        return created

    # --------------------------------------------------------------- students
    def _create_students(
        self,
        *,
        rng: random.Random,
        count: int,
        foreign_count: int,
        classes: list[SchoolClass],
        year: AcademicYear,
        actor: User | None,
        guardians_cache: list[Guardian],
        seq_start: int,
    ) -> tuple[list[Student], int]:
        weights = []
        for klass in classes:
            if klass.level.code in {"7E", "8E"}:
                weights.append(3.0)
            elif klass.level.code in {"1E", "2E"}:
                weights.append(2.0)
            else:
                weights.append(1.5)

        slots: list[SchoolClass] = []
        remaining = count
        raw = [w / sum(weights) * count for w in weights]
        floors = [int(x) for x in raw]
        for i, n in enumerate(floors):
            slots.extend([classes[i]] * n)
            remaining -= n
        order = sorted(range(len(classes)), key=lambda i: weights[i], reverse=True)
        for i in order:
            if remaining <= 0:
                break
            slots.append(classes[i])
            remaining -= 1
        rng.shuffle(slots)
        slots = slots[:count]

        foreign_indexes = set(rng.sample(range(count), min(foreign_count, count)))
        students: list[Student] = []
        admission_base = year.start_date - timedelta(days=20)
        seq = seq_start

        for idx, klass in enumerate(slots):
            seq += 1
            is_foreign = idx in foreign_indexes
            sexe = rng.choice([Student.Gender.MALE, Student.Gender.FEMALE])
            prenom = rng.choice(PRENOMS_M if sexe == Student.Gender.MALE else PRENOMS_F)

            if is_foreign:
                nationalite, lieu_a, lieu_b = rng.choice(FOREIGN)
                lieu = rng.choice([lieu_a, lieu_b])
                nom = rng.choice(
                    ("Banda", "Phiri", "Mwale", "Tembo", "Chirwa", "Okello", "Nkurunziza", "Uwamahoro")
                )
                postnom = ""
                adresse = f"Avenue Frontière, {rng.choice(QUARTIERS_LIKASI)}, Likasi"
            else:
                nationalite = "Congolaise"
                lieu = rng.choice(LIEUX_NAISSANCE)
                nom = rng.choice(NOMS)
                postnom = rng.choice(POSTNOMS)
                adresse = (
                    f"Avenue {rng.choice(('Lumumba', 'Mobutu', 'Kasavubu', 'Sendwe', 'Likasi'))} "
                    f"n°{rng.randint(1, 240)}, {rng.choice(QUARTIERS_LIKASI)}, Likasi"
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

            matricule = f"KAL{year.start_date.year}{seq:05d}"
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
                ancien_etablissement=rng.choice(ETABLISSEMENTS) if rng.random() < 0.45 else "",
                date_admission=admission_base + timedelta(days=rng.randint(0, 40)),
                statut=Student.Status.ACTIVE,
                is_active=True,
                is_archived=False,
                groupe_sanguin=rng.choice(BLOOD) if rng.random() < 0.7 else "",
                allergies="Arachides" if rng.random() < 0.04 else "",
                observations="",
            )
            students.append(student)

            if guardians_cache and rng.random() < 0.18:
                guardian = rng.choice(guardians_cache)
            else:
                g_sexe = rng.choice([Guardian.Gender.MALE, Guardian.Gender.FEMALE])
                g_prenom = rng.choice(PRENOMS_M if g_sexe == Guardian.Gender.MALE else PRENOMS_F)
                phone = f"+243{rng.choice((81, 82, 84, 85, 97, 99))}{rng.randint(1000000, 9999999)}"
                guardian = Guardian.objects.create(
                    nom=nom if not is_foreign and rng.random() < 0.55 else rng.choice(NOMS),
                    postnom=rng.choice(POSTNOMS) if not is_foreign else "",
                    prenom=g_prenom,
                    sexe=g_sexe,
                    telephone_principal=phone,
                    telephone_secondaire=(
                        f"+243{rng.choice((81, 97))}{rng.randint(1000000, 9999999)}"
                        if rng.random() < 0.35
                        else ""
                    ),
                    email=(
                        f"{g_prenom.lower()}.{nom.lower().replace(' ', '')}{rng.randint(1, 99)}@gmail.com"
                        if rng.random() < 0.4
                        else ""
                    ),
                    adresse=adresse,
                    profession=rng.choice(PROFESSIONS),
                    numero_identification=(
                        f"CD{rng.randint(10_000_000, 99_999_999)}" if rng.random() < 0.5 else ""
                    ),
                    is_active=True,
                )
                guardians_cache.append(guardian)

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
                enrollment_number=f"INS{year.start_date.year}{seq:05d}",
                enrollment_type=rng.choice(
                    [
                        Enrollment.EnrollmentType.NEW,
                        Enrollment.EnrollmentType.NEW,
                        Enrollment.EnrollmentType.RENEWAL,
                        Enrollment.EnrollmentType.INCOMING_TRANSFER,
                    ]
                ),
                enrollment_date=student.date_admission,
                status=Enrollment.Status.VALIDATED,
                provenance=student.ancien_etablissement,
                created_by=actor,
            )
            student._seed_enrollment = enrollment  # type: ignore[attr-defined]

        return students, seq

    # -------------------------------------------------------- docs / cards / coms
    def _create_documents(
        self,
        rng: random.Random,
        students: list[Student],
        actor: User | None,
    ) -> None:
        types = list(DocumentType.objects.filter(is_active=True))
        if not types:
            return
        sample = rng.sample(students, k=max(1, int(len(students) * 0.35)))
        for student in sample:
            for doc_type in rng.sample(types, k=rng.randint(1, min(3, len(types)))):
                status = rng.choice(
                    [
                        StudentDocument.VerificationStatus.PENDING,
                        StudentDocument.VerificationStatus.VALIDATED,
                        StudentDocument.VerificationStatus.VALIDATED,
                        StudentDocument.VerificationStatus.REJECTED,
                    ]
                )
                doc = StudentDocument(
                    student=student,
                    document_type=doc_type,
                    verification_status=status,
                    received_at=timezone.now() - timedelta(days=rng.randint(1, 120)),
                    verified_by=actor if status != StudentDocument.VerificationStatus.PENDING else None,
                    observation="Document incomplet" if status == StudentDocument.VerificationStatus.REJECTED else "",
                )
                doc.file.save(
                    f"{student.matricule}_{doc_type.code}.pdf",
                    ContentFile(b"%PDF-1.4 demo document Kalunga\n"),
                    save=False,
                )
                doc.save()

    def _create_cards(self, students: list[Student], actor: User | None) -> None:
        from apps.secretariat.services.card_service import generate_card

        for student in students:
            enrollment = getattr(student, "_seed_enrollment", None)
            if enrollment is None:
                continue
            if enrollment.status != Enrollment.Status.VALIDATED:
                continue
            try:
                generate_card(enrollment=enrollment, actor=actor)
            except Exception as exc:  # noqa: BLE001 — continue seeding
                self.stderr.write(f"Carte non générée pour {student.matricule}: {exc}")

    def _create_communications(
        self,
        year: AcademicYear,
        levels: dict[str, SchoolLevel],
        sections: dict[str, Section],
        classes: list[SchoolClass],
        actor: User | None,
        rng: random.Random,
    ) -> None:
        now = timezone.now()
        y = year.label
        start_year = year.start_date.year
        science_class = next((c for c in classes if c.code.startswith("4E-SCIENCE")), classes[0])

        specs = [
            (
                f"Rentrée scolaire {y}",
                f"Chers parents, la rentrée {y} est fixée au lundi 1er septembre {start_year} à 07h30. "
                "Chaque élève doit se présenter en uniforme complet avec son dossier.",
                Communication.Category.ADMINISTRATIVE,
                Communication.Priority.IMPORTANT,
                CommunicationTarget.TargetType.ALL_PARENTS,
                {},
                year.is_active,
            ),
            (
                f"Réunion des parents — 7ème et 8ème ({y})",
                "Une réunion d'information pour les parents du tronc commun se tiendra "
                f"le samedi 20 septembre {start_year} dans la grande salle.",
                Communication.Category.ACADEMIC,
                Communication.Priority.NORMAL,
                CommunicationTarget.TargetType.LEVEL,
                {"level": levels["7E"]},
                False,
            ),
            (
                f"Sortie pédagogique — Electricité ({y})",
                "Visite technique prévue pour les classes d'Electricité. "
                "Autorisation parentale obligatoire.",
                Communication.Category.EVENT,
                Communication.Priority.IMPORTANT,
                CommunicationTarget.TargetType.SECTION,
                {"section": sections["EL"]},
                False,
            ),
            (
                f"Paiement du minerval — 2e tranche ({y})",
                f"Rappel : la deuxième tranche du minerval doit être soldée avant le 15 novembre {start_year} "
                "auprès de la caisse de l'établissement (BP 74 Likasi).",
                Communication.Category.ADMINISTRATIVE,
                Communication.Priority.URGENT,
                CommunicationTarget.TargetType.ACADEMIC_YEAR,
                {"academic_year": year},
                year.is_active,
            ),
            (
                f"Journée culturelle Institut Kalunga ({y})",
                "Spectacle et stands des sections Scientifique, Pédagogie, Commerciale & gestion, "
                "Mécanique générale et Electricité. Ouvert aux familles.",
                Communication.Category.GENERAL,
                Communication.Priority.NORMAL,
                CommunicationTarget.TargetType.ALL_PARENTS,
                {},
                False,
            ),
            (
                f"Contrôles de fin de trimestre ({y})",
                "Le calendrier des contrôles de fin de 1er trimestre sera affiché dès lundi. "
                "Merci de veiller à la présence régulière des élèves.",
                Communication.Category.ACADEMIC,
                Communication.Priority.NORMAL,
                CommunicationTarget.TargetType.CLASS,
                {"school_class": science_class},
                False,
            ),
        ]

        for title, content, category, priority, target_type, target_kwargs, pinned in specs:
            status = (
                Communication.Status.PUBLISHED
                if year.is_active and not year.is_closed
                else Communication.Status.ARCHIVED
            )

            com = Communication.objects.create(
                title=title,
                content=content,
                category=category,
                priority=priority,
                status=status,
                published_at=now - timedelta(days=rng.randint(1, 40)),
                expires_at=now + timedelta(days=90) if status == Communication.Status.PUBLISHED else None,
                author=actor,
                is_pinned=pinned and status == Communication.Status.PUBLISHED,
                pinned_at=now if pinned and status == Communication.Status.PUBLISHED else None,
                pinned_by=actor if pinned and status == Communication.Status.PUBLISHED else None,
            )
            CommunicationTarget.objects.create(
                communication=com,
                target_type=target_type,
                **target_kwargs,
            )

        if year.is_active and not year.is_closed:
            draft = Communication.objects.create(
                title="Brouillon — Note aux enseignants",
                content="Texte en préparation concernant le suivi des absences.",
                category=Communication.Category.ADMINISTRATIVE,
                priority=Communication.Priority.NORMAL,
                status=Communication.Status.DRAFT,
                author=actor,
                is_pinned=False,
            )
            CommunicationTarget.objects.create(
                communication=draft,
                target_type=CommunicationTarget.TargetType.ALL_PARENTS,
            )

    def _summary(self, years: list[AcademicYear]) -> str:
        return (
            "Seed multi-années terminé — "
            f"{len(years)} années scolaires, "
            f"{SchoolLevel.objects.count()} niveaux, "
            f"{Section.objects.count()} sections, "
            f"{Option.objects.count()} options, "
            f"{SchoolClass.objects.count()} classes, "
            f"{Student.objects.count()} élèves, "
            f"{Guardian.objects.count()} responsables, "
            f"{Enrollment.objects.count()} inscriptions, "
            f"{StudentCard.objects.count()} cartes, "
            f"{StudentDocument.objects.count()} documents, "
            f"{Communication.objects.count()} communications.\n"
            f"Année active : {ACTIVE_YEAR_LABEL} · Toutes les autres années : clôturées."
        )
