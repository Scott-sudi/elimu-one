"""Discipline core models (attendance and conduct categories)."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.secretariat.models import AcademicYear, Enrollment, SchoolClass, SchoolLevel, Student
from apps.secretariat.models.base import TimeStampedPublicIdModel


class ConductCategory(TimeStampedPublicIdModel):
    """Configurable conduct/incident categories."""

    class ObservationType(models.TextChoices):
        POSITIVE = "POSITIVE", "Favorable"
        NEGATIVE = "NEGATIVE", "Défavorable"
        NEUTRAL = "NEUTRE", "Neutre"

    class Severity(models.TextChoices):
        LOW = "FAIBLE", "Faible"
        MODERATE = "MODERE", "Modéré"
        HIGH = "GRAVE", "Grave"
        VERY_HIGH = "TRES_GRAVE", "Très grave"

    code = models.CharField("Code", max_length=40, unique=True)
    name = models.CharField("Nom", max_length=140, db_index=True)
    observation_type = models.CharField(
        "Type d'observation",
        max_length=10,
        choices=ObservationType.choices,
        default=ObservationType.NEGATIVE,
        db_index=True,
    )
    description = models.TextField("Description", blank=True)
    default_severity = models.CharField(
        "Gravité par défaut",
        max_length=12,
        choices=Severity.choices,
        default=Severity.MODERATE,
        db_index=True,
    )
    is_active = models.BooleanField("Active", default=True, db_index=True)
    is_archived = models.BooleanField("Archivée", default=False, db_index=True)

    class Meta:
        ordering = ["observation_type", "name"]
        verbose_name = "Catégorie de conduite"
        verbose_name_plural = "Catégories de conduite"
        indexes = [
            models.Index(fields=["observation_type", "is_active"]),
            models.Index(fields=["default_severity", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class AttendanceSchedule(TimeStampedPublicIdModel):
    """Expected schedule used to compute late minutes."""

    class Vacation(models.TextChoices):
        MORNING = "AVANT_MIDI", "Avant-midi"
        AFTERNOON = "APRES_MIDI", "Après-midi"

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="attendance_schedules",
        verbose_name="Année scolaire",
    )
    level = models.ForeignKey(
        SchoolLevel,
        on_delete=models.PROTECT,
        related_name="attendance_schedules",
        null=True,
        blank=True,
        verbose_name="Niveau",
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="attendance_schedules",
        null=True,
        blank=True,
        verbose_name="Classe",
    )
    vacation = models.CharField(
        "Vacation",
        max_length=12,
        choices=Vacation.choices,
        blank=True,
        db_index=True,
        help_text="Avant-midi ou après-midi (horaire général pour les classes de cette vacation).",
    )
    label = models.CharField("Libellé", max_length=120)
    start_time = models.TimeField("Début des cours")
    present_until = models.TimeField(
        "Présent jusqu'à",
        null=True,
        blank=True,
        help_text="Fin de tolérance : après cette heure, l'élève est en retard.",
    )
    tolerance_minutes = models.PositiveSmallIntegerField("Tolérance (minutes)", default=0)
    end_time = models.TimeField("Fin des cours", null=True, blank=True)
    is_active = models.BooleanField("Active", default=True, db_index=True)
    is_archived = models.BooleanField("Archivée", default=False, db_index=True)

    class Meta:
        ordering = ["academic_year", "vacation", "school_class__name", "level__order", "label"]
        verbose_name = "Horaire de pointage"
        verbose_name_plural = "Horaires de pointage"
        constraints = [
            models.CheckConstraint(
                condition=Q(tolerance_minutes__gte=0),
                name="discipline_schedule_tolerance_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["academic_year", "is_active"]),
            models.Index(fields=["school_class", "is_active"]),
            models.Index(fields=["level", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.label

    def get_present_until(self):
        """Return the latest arrival time still counted as present."""
        if self.present_until:
            return self.present_until
        from datetime import datetime, timedelta

        base = datetime.combine(datetime.min.date(), self.start_time)
        return (base + timedelta(minutes=int(self.tolerance_minutes or 0))).time()

    def sync_tolerance_from_present_until(self) -> None:
        """Keep tolerance_minutes aligned with present_until for legacy callers."""
        if not self.present_until or not self.start_time:
            return
        from datetime import datetime

        start = datetime.combine(datetime.min.date(), self.start_time)
        until = datetime.combine(datetime.min.date(), self.present_until)
        delta = int((until - start).total_seconds() // 60)
        self.tolerance_minutes = max(delta, 0)


class DailyAttendance(TimeStampedPublicIdModel):
    """Main daily attendance record: one row per enrollment per date."""

    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Présent"
        LATE = "RETARD", "Retard"
        ABSENT = "ABSENT", "Absent"
        JUSTIFIED_ABSENCE = "ABSENCE_JUSTIFIEE", "Absence justifiée"
        SICK = "MALADE", "Malade"
        EXEMPTED = "DISPENSE", "Dispensé"
        AUTHORIZED_EXIT = "SORTIE_AUTORISEE", "Sortie autorisée"
        TEMP_SENT_HOME = "RENVOYE_TEMP", "Renvoyé temporairement"

    class Source(models.TextChoices):
        QR = "QR", "QR"
        MANUAL = "MANUEL", "Manuel"
        IMPORT = "IMPORT", "Import"

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="daily_attendances",
        verbose_name="Année scolaire",
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="daily_attendances",
        verbose_name="Inscription",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="daily_attendances",
        verbose_name="Élève",
    )
    date = models.DateField("Date", db_index=True)
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT,
        db_index=True,
    )
    arrival_time = models.TimeField("Heure d'arrivée", null=True, blank=True)
    exit_time = models.TimeField("Heure de sortie", null=True, blank=True)
    late_minutes = models.PositiveIntegerField("Minutes de retard", default=0)
    source = models.CharField(
        "Source du pointage",
        max_length=12,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="recorded_attendances",
        null=True,
        blank=True,
        verbose_name="Enregistré par",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="modified_attendances",
        null=True,
        blank=True,
        verbose_name="Modifié par",
    )
    modification_reason = models.TextField("Motif de modification", blank=True)
    note = models.TextField("Observation", blank=True)
    is_day_closed = models.BooleanField("Journée clôturée", default=False, db_index=True)

    class Meta:
        ordering = ["-date", "enrollment__school_class__name", "student__nom", "student__prenom"]
        verbose_name = "Présence journalière"
        verbose_name_plural = "Présences journalières"
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "date"],
                name="discipline_unique_attendance_per_enrollment_day",
            ),
            models.CheckConstraint(
                condition=Q(late_minutes__gte=0),
                name="discipline_attendance_late_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["academic_year", "date"]),
            models.Index(fields=["status", "date"]),
            models.Index(fields=["enrollment", "date"]),
            models.Index(fields=["student", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.date} ({self.status})"


class AttendanceScanEvent(TimeStampedPublicIdModel):
    """Raw scan history to preserve attempts and duplicates."""

    class EventType(models.TextChoices):
        ARRIVAL = "ARRIVEE", "Arrivée"
        EXIT = "SORTIE", "Sortie"

    class Result(models.TextChoices):
        SUCCESS = "SUCCES", "Succès"
        DUPLICATE = "DOUBLE", "Doublon"
        BLOCKED_CARD = "CARTE_BLOQUEE", "Carte bloquée"
        UNKNOWN_QR = "QR_INCONNU", "QR inconnu"
        WRONG_YEAR = "ANNEE_INVALIDE", "Année invalide"
        INACTIVE_ENROLLMENT = "INSCRIPTION_INACTIVE", "Inscription inactive"
        ERROR = "ERREUR", "Erreur"

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="attendance_scan_events",
        verbose_name="Année scolaire",
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="attendance_scan_events",
        null=True,
        blank=True,
        verbose_name="Inscription",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="attendance_scan_events",
        null=True,
        blank=True,
        verbose_name="Élève",
    )
    event_type = models.CharField(
        "Type d'événement",
        max_length=10,
        choices=EventType.choices,
        db_index=True,
    )
    result = models.CharField("Résultat", max_length=22, choices=Result.choices, db_index=True)
    scanned_at = models.DateTimeField("Scanné le", db_index=True)
    qr_identifier = models.CharField("Identifiant QR", max_length=255, blank=True)
    message = models.CharField("Message", max_length=255, blank=True)
    scanner_device = models.CharField("Appareil", max_length=120, blank=True)
    scanned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="discipline_scan_events",
        null=True,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-scanned_at", "-created_at"]
        verbose_name = "Événement de scan"
        verbose_name_plural = "Événements de scan"
        indexes = [
            models.Index(fields=["academic_year", "scanned_at"]),
            models.Index(fields=["enrollment", "scanned_at"]),
            models.Index(fields=["result", "scanned_at"]),
            models.Index(fields=["event_type", "scanned_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} {self.result} {self.scanned_at:%Y-%m-%d %H:%M}"


class ClassAttendanceSheet(TimeStampedPublicIdModel):
    """Daily attendance folder (one class + one date)."""

    class Status(models.TextChoices):
        NOT_STARTED = "NON_SAISIE", "Non saisie"
        DRAFT = "BROUILLON", "Brouillon"
        VALIDATED = "VALIDEE", "Validée"
        CLOSED = "CLOTUREE", "Clôturée"

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="attendance_sheets",
        verbose_name="Année scolaire",
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="attendance_sheets",
        verbose_name="Classe",
    )
    date = models.DateField("Date", db_index=True)
    status = models.CharField(
        "Statut",
        max_length=12,
        choices=Status.choices,
        default=Status.NOT_STARTED,
        db_index=True,
    )
    total_students = models.PositiveIntegerField(default=0)
    total_present = models.PositiveIntegerField(default=0)
    total_absent = models.PositiveIntegerField(default=0)
    total_unmarked = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_attendance_sheets",
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_attendance_sheets",
    )
    validation_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_attendance_sheets",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    modification_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "school_class__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school_class", "date"],
                name="discipline_unique_class_sheet_per_day",
            )
        ]
        indexes = [
            models.Index(fields=["academic_year", "date"]),
            models.Index(fields=["school_class", "date"]),
            models.Index(fields=["status", "date"]),
        ]


class StudentAttendanceRecord(TimeStampedPublicIdModel):
    """Attendance line for a student inside a class daily sheet."""

    class Status(models.TextChoices):
        UNMARKED = "NON_MARQUE", "Non marqué"
        PRESENT = "PRESENT", "Présent"
        ABSENT = "ABSENT", "Absent"

    class Mention(models.TextChoices):
        OK = "OK", "OK"
        ABS = "ABS", "ABS"

    sheet = models.ForeignKey(
        ClassAttendanceSheet,
        on_delete=models.CASCADE,
        related_name="records",
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="sheet_attendance_records",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="sheet_attendance_records",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.UNMARKED,
        db_index=True,
    )
    presence_value = models.SmallIntegerField(null=True, blank=True)
    mention = models.CharField(max_length=6, blank=True)
    observation = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_sheet_attendance_records",
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="sheet_attendance_records",
    )

    class Meta:
        ordering = ["student__nom", "student__prenom"]
        constraints = [
            models.UniqueConstraint(
                fields=["sheet", "enrollment"],
                name="discipline_unique_sheet_record_per_enrollment",
            ),
            models.CheckConstraint(
                condition=Q(presence_value__in=[0, 1]) | Q(presence_value__isnull=True),
                name="discipline_record_presence_value_allowed",
            ),
            models.CheckConstraint(
                condition=(
                    (Q(status="NON_MARQUE") & Q(presence_value__isnull=True) & Q(mention=""))
                    | (Q(status="PRESENT") & Q(presence_value=1) & Q(mention="OK"))
                    | (Q(status="ABSENT") & Q(presence_value=0) & Q(mention="ABS"))
                ),
                name="discipline_record_status_value_mention_consistent",
            ),
        ]
        indexes = [
            models.Index(fields=["sheet", "status"]),
            models.Index(fields=["enrollment", "status"]),
            models.Index(fields=["student", "status"]),
            models.Index(fields=["school_class", "status"]),
        ]

    def apply_status(self, status: str):
        if status == self.Status.PRESENT:
            self.status = self.Status.PRESENT
            self.presence_value = 1
            self.mention = self.Mention.OK
        elif status == self.Status.ABSENT:
            self.status = self.Status.ABSENT
            self.presence_value = 0
            self.mention = self.Mention.ABS
        else:
            self.status = self.Status.UNMARKED
            self.presence_value = None
            self.mention = ""

    def save(self, *args, **kwargs):
        self.apply_status(self.status)
        if self.school_class_id is None and self.sheet_id:
            self.school_class_id = self.sheet.school_class_id
        super().save(*args, **kwargs)


class DisciplinaryIncident(TimeStampedPublicIdModel):
    """Disciplinary incident raised for one class/student context."""

    class Severity(models.TextChoices):
        LOW = "FAIBLE", "Faible"
        MODERATE = "MODERE", "Modéré"
        HIGH = "GRAVE", "Grave"
        VERY_HIGH = "TRES_GRAVE", "Très grave"

    class Status(models.TextChoices):
        DRAFT = "BROUILLON", "Brouillon"
        REPORTED = "SIGNALE", "Signalé"
        REVIEW = "EN_EXAMEN", "En examen"
        CONFIRMED = "CONFIRME", "Confirmé"
        DISMISSED = "CLASSE_SANS_SUITE", "Classé sans suite"
        CLOSED = "CLOTURE", "Clôturé"
        ARCHIVED = "ARCHIVE", "Archivé"

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="disciplinary_incidents",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="disciplinary_incidents",
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="disciplinary_incidents",
    )
    category = models.ForeignKey(
        ConductCategory,
        on_delete=models.PROTECT,
        related_name="incidents",
    )
    title = models.CharField("Titre", max_length=180)
    description = models.TextField("Description")
    incident_date = models.DateField("Date d'incident", db_index=True)
    incident_time = models.TimeField("Heure", null=True, blank=True)
    location = models.CharField("Lieu", max_length=140, blank=True)
    severity = models.CharField(
        "Gravité",
        max_length=12,
        choices=Severity.choices,
        default=Severity.MODERATE,
        db_index=True,
    )
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_discipline_incidents",
    )
    witnesses = models.TextField("Témoins", blank=True)
    immediate_action = models.TextField("Action immédiate", blank=True)
    needs_summons = models.BooleanField("Nécessite convocation", default=False)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_discipline_incidents",
    )
    confirmed_at = models.DateTimeField("Confirmé le", null=True, blank=True)
    closed_at = models.DateTimeField("Clôturé le", null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_discipline_incidents",
    )
    closure_note = models.TextField("Observation de clôture", blank=True)
    is_archived = models.BooleanField("Archivé", default=False, db_index=True)

    class Meta:
        ordering = ["-incident_date", "-created_at"]
        indexes = [
            models.Index(fields=["academic_year", "incident_date"]),
            models.Index(fields=["school_class", "status"]),
            models.Index(fields=["student", "status"]),
            models.Index(fields=["severity", "status"]),
        ]


class IncidentParticipant(TimeStampedPublicIdModel):
    """Additional students involved in an incident."""

    class Role(models.TextChoices):
        SUBJECT = "CONCERNE", "Concerné"
        WITNESS = "TEMOIN", "Témoin"
        VICTIM = "VICTIME", "Victime"
        OTHER = "AUTRE", "Autre"

    incident = models.ForeignKey(
        DisciplinaryIncident,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="incident_participations",
    )
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.SUBJECT)
    note = models.TextField(blank=True)
    is_confirmed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["incident", "student"],
                name="discipline_unique_incident_participant",
            )
        ]


class DisciplinaryMeasureType(TimeStampedPublicIdModel):
    class MinSeverity(models.TextChoices):
        LOW = "FAIBLE", "Faible"
        MODERATE = "MODERE", "Modéré"
        HIGH = "GRAVE", "Grave"
        VERY_HIGH = "TRES_GRAVE", "Très grave"

    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=140, db_index=True)
    description = models.TextField(blank=True)
    minimum_severity = models.CharField(
        max_length=12,
        choices=MinSeverity.choices,
        default=MinSeverity.LOW,
    )
    requires_validation = models.BooleanField(default=True)
    max_duration_days = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["name"]


class DisciplinaryMeasure(TimeStampedPublicIdModel):
    class Status(models.TextChoices):
        PROPOSED = "PROPOSEE", "Proposée"
        VALIDATED = "VALIDEE", "Validée"
        IN_PROGRESS = "EN_COURS", "En cours"
        EXECUTED = "EXECUTEE", "Exécutée"
        CANCELLED = "ANNULEE", "Annulée"
        CLOSED = "CLOTUREE", "Clôturée"

    incident = models.ForeignKey(
        DisciplinaryIncident,
        on_delete=models.PROTECT,
        related_name="measures",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="disciplinary_measures",
    )
    measure_type = models.ForeignKey(
        DisciplinaryMeasureType,
        on_delete=models.PROTECT,
        related_name="measures",
    )
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROPOSED, db_index=True)
    reason = models.TextField(blank=True)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_discipline_measures",
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_discipline_measures",
    )
    validation_date = models.DateTimeField(null=True, blank=True)
    execution_date = models.DateTimeField(null=True, blank=True)
    result_note = models.TextField(blank=True)
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["student", "status"]),
        ]


class ParentSummons(TimeStampedPublicIdModel):
    class Status(models.TextChoices):
        DRAFT = "BROUILLON", "Brouillon"
        SCHEDULED = "PROGRAMMEE", "Programmée"
        SENT = "TRANSMISE", "Transmise"
        RECEIVED = "RECUE", "Reçue"
        CONFIRMED = "CONFIRMEE", "Confirmée"
        PRESENT = "RESPONSABLE_PRESENT", "Responsable présent"
        ABSENT = "RESPONSABLE_ABSENT", "Responsable absent"
        POSTPONED = "REPORTEE", "Reportée"
        CANCELLED = "ANNULEE", "Annulée"
        CLOSED = "CLOTUREE", "Clôturée"
        ARCHIVED = "ARCHIVEE", "Archivée"

    class DeliveryMode(models.TextChoices):
        PAPER = "PAPIER", "Remise papier"
        PHONE = "APPEL", "Appel téléphonique"
        SMS = "SMS", "SMS"
        EMAIL = "EMAIL", "E-mail"
        MOBILE_APP = "APP", "Application mobile"
        OTHER = "AUTRE", "Autre"

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="summonses",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="summonses",
    )
    incident = models.ForeignKey(
        DisciplinaryIncident,
        on_delete=models.SET_NULL,
        related_name="summonses",
        null=True,
        blank=True,
    )
    summon_number = models.CharField(max_length=40, unique=True)
    reason = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    summon_date = models.DateField(db_index=True)
    summon_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_summonses",
    )
    target_guardians = models.ManyToManyField(
        "secretariat.Guardian",
        blank=True,
        related_name="discipline_summonses",
    )
    delivery_mode = models.CharField(max_length=12, choices=DeliveryMode.choices, default=DeliveryMode.PAPER)
    delivery_date = models.DateTimeField(null=True, blank=True)
    acknowledgement = models.BooleanField(default=False)
    acknowledgement_date = models.DateTimeField(null=True, blank=True)
    meeting_date = models.DateTimeField(null=True, blank=True)
    meeting_result = models.TextField(blank=True)
    decision = models.TextField(blank=True)
    next_action = models.TextField(blank=True)
    followup_date = models.DateField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_summonses",
    )
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-summon_date", "-created_at"]
        indexes = [
            models.Index(fields=["academic_year", "summon_date"]),
            models.Index(fields=["status", "summon_date"]),
            models.Index(fields=["student", "status"]),
        ]


class AbsenceJustification(TimeStampedPublicIdModel):
    class Status(models.TextChoices):
        PENDING = "EN_ATTENTE", "En attente"
        ACCEPTED = "ACCEPTE", "Accepté"
        REJECTED = "REJETE", "Rejeté"
        ARCHIVED = "ARCHIVE", "Archivé"

    attendance = models.ForeignKey(
        DailyAttendance,
        on_delete=models.PROTECT,
        related_name="justifications",
    )
    reason = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    document = models.FileField(upload_to="discipline/justifications/%Y/", blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_absence_justifications",
    )
    submitted_at = models.DateTimeField(default=timezone.now, db_index=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_absence_justifications",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [models.Index(fields=["status", "submitted_at"])]


class ExitAuthorization(TimeStampedPublicIdModel):
    class Status(models.TextChoices):
        REQUESTED = "DEMANDEE", "Demandée"
        AUTHORIZED = "AUTORISEE", "Autorisée"
        REFUSED = "REFUSEE", "Refusée"
        EXITED = "SORTIE_EFFECTUEE", "Sortie effectuée"
        RETURNED = "RETOUR_EFFECTUE", "Retour effectué"
        CANCELLED = "ANNULEE", "Annulée"

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="exit_authorizations",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="exit_authorizations",
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="exit_authorizations",
    )
    date = models.DateField(db_index=True)
    planned_exit_time = models.TimeField(null=True, blank=True)
    actual_exit_time = models.TimeField(null=True, blank=True)
    reason = models.TextField()
    requesting_guardian = models.CharField(max_length=180, blank=True)
    guardian_contact = models.CharField(max_length=50, blank=True)
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authorized_exits",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    expected_return_time = models.TimeField(null=True, blank=True)
    actual_return_time = models.TimeField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["academic_year", "date"]),
            models.Index(fields=["status", "date"]),
            models.Index(fields=["student", "status"]),
        ]
