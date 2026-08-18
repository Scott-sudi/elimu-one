"""Vide les données métier de test pour démarrer en production réelle.

Conserve :
- la base MySQL elle-même (pas de DROP DATABASE)
- le fichier .env
- staticfiles / code
- comptes staff / admin + rôles
- SystemConfiguration + paramètres secrétariat

Supprime :
- élèves, responsables, inscriptions, classes, années
- finance, discipline, communications, push parents, audit
- fichiers media liés aux élèves / reçus (si présents)
"""

from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


CONFIRM_TOKEN = "OUI_JE_VIDE_LES_DONNEES_TEST"


class Command(BaseCommand):
    help = (
        "Purge les données opérationnelles (test/démo) pour un démarrage vierge. "
        f"Obligatoire : --confirm={CONFIRM_TOKEN}"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            required=True,
            help=f"Doit être exactement : {CONFIRM_TOKEN}",
        )
        parser.add_argument(
            "--keep-catalog",
            action="store_true",
            help="Garder les catalogues (catégories de conduite, types de documents, catégories de frais).",
        )

    def handle(self, *args, **options):
        if options["confirm"] != CONFIRM_TOKEN:
            raise CommandError(
                "Confirmation invalide. Relancez avec "
                f"--confirm={CONFIRM_TOKEN}"
            )

        self.stdout.write(self.style.WARNING("=== PURGE DONNÉES MÉTIER (production) ==="))
        self.stdout.write("Base conservée. .env conservé. Comptes staff conservés.")

        keep_catalog = bool(options["keep_catalog"])
        counts_before = self._snapshot_counts()

        with transaction.atomic():
            self._purge(keep_catalog=keep_catalog)

        self._clear_media_dirs()
        Session.objects.all().delete()

        counts_after = self._snapshot_counts()
        self.stdout.write("")
        self.stdout.write("Avant → Après (extraits) :")
        for key in sorted(counts_before.keys()):
            self.stdout.write(f"  {key}: {counts_before[key]} → {counts_after.get(key, 0)}")

        from apps.accounts.models import User

        staff_n = User.objects.filter(is_staff=True).count()
        self.stdout.write(self.style.SUCCESS(f"PURGE_OK — comptes staff restants : {staff_n}"))
        self.stdout.write(
            "Prochaine étape côté école : créer l'année scolaire, les niveaux/classes, "
            "puis les responsables et élèves."
        )

    def _set_fk_checks(self, enabled: bool) -> None:
        if connection.vendor == "mysql":
            with connection.cursor() as cursor:
                cursor.execute(f"SET FOREIGN_KEY_CHECKS={1 if enabled else 0}")

    def _safe_delete(self, model, label: str) -> int:
        try:
            n, _ = model.objects.all().delete()
            self.stdout.write(f"  - {label}: {n}")
            return n
        except Exception as exc:  # noqa: BLE001
            self.stderr.write(f"  ! {label}: ignoré ({exc})")
            return 0

    def _purge(self, *, keep_catalog: bool) -> None:
        from apps.api.models import ParentAttendanceNoticeRead, ParentPushDevice
        from apps.audit.models import AuditLog, LoginAttempt
        from apps.discipline.models import (
            AbsenceJustification,
            AttendanceScanEvent,
            AttendanceSchedule,
            ClassAttendanceSheet,
            ConductCategory,
            DailyAttendance,
            DisciplinaryIncident,
            DisciplinaryMeasure,
            DisciplinaryMeasureType,
            ExitAuthorization,
            IncidentParticipant,
            ParentSummons,
            StudentAttendanceRecord,
        )
        from apps.finance.models import (
            FeeAmountChangeRequest,
            FeeApprovalHistory,
            FeeCategory,
            FeeClassAmount,
            FeeRevisionRequest,
            FeeTarget,
            Payment,
            PaymentAllocation,
            ReceiptSequence,
            SchoolFee,
            StudentFeeObligation,
        )
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

        self._set_fk_checks(False)
        try:
            self.stdout.write("API parents…")
            self._safe_delete(ParentAttendanceNoticeRead, "lectures notifs présence")
            self._safe_delete(ParentPushDevice, "appareils push parents")

            self.stdout.write("Finance…")
            self._safe_delete(PaymentAllocation, "allocations paiement")
            self._safe_delete(Payment, "paiements")
            self._safe_delete(StudentFeeObligation, "obligations frais")
            self._safe_delete(FeeAmountChangeRequest, "demandes montant frais")
            self._safe_delete(FeeRevisionRequest, "révisions frais")
            self._safe_delete(FeeClassAmount, "montants frais/classe")
            self._safe_delete(FeeApprovalHistory, "historique approbation frais")
            self._safe_delete(FeeTarget, "cibles frais")
            self._safe_delete(SchoolFee, "frais scolaires")
            self._safe_delete(ReceiptSequence, "séquences reçus")
            if not keep_catalog:
                self._safe_delete(FeeCategory, "catégories frais")

            self.stdout.write("Discipline…")
            self._safe_delete(IncidentParticipant, "participants incidents")
            self._safe_delete(DisciplinaryMeasure, "mesures disciplinaires")
            self._safe_delete(ParentSummons, "convocations")
            self._safe_delete(AbsenceJustification, "justifications absence")
            self._safe_delete(ExitAuthorization, "sorties autorisées")
            self._safe_delete(DisciplinaryIncident, "incidents")
            self._safe_delete(StudentAttendanceRecord, "lignes feuille présence")
            self._safe_delete(ClassAttendanceSheet, "feuilles présence")
            self._safe_delete(AttendanceScanEvent, "scans présence")
            self._safe_delete(DailyAttendance, "présences journalières")
            self._safe_delete(AttendanceSchedule, "horaires présence")
            if not keep_catalog:
                self._safe_delete(DisciplinaryMeasureType, "types de mesures")
                self._safe_delete(ConductCategory, "catégories de conduite")

            self.stdout.write("Secrétariat…")
            self._safe_delete(CommunicationReceipt, "accusés messages")
            self._safe_delete(CommunicationTarget, "cibles messages")
            self._safe_delete(Communication, "communications")
            self._safe_delete(StudentDocument, "documents élèves")
            self._safe_delete(StudentCard, "cartes élèves")
            self._safe_delete(ClassTransfer, "transferts de classe")
            self._safe_delete(Enrollment, "inscriptions")
            self._safe_delete(StudentGuardian, "liens élève-responsable")
            self._safe_delete(Student, "élèves")
            self._safe_delete(Guardian, "responsables")
            self._safe_delete(SchoolClass, "classes")
            self._safe_delete(Option, "options")
            self._safe_delete(Section, "sections")
            self._safe_delete(SchoolLevel, "niveaux")
            self._safe_delete(AcademicYear, "années scolaires")
            if not keep_catalog:
                self._safe_delete(DocumentType, "types de documents")

            self.stdout.write("Audit…")
            self._safe_delete(AuditLog, "journal d'audit")
            self._safe_delete(LoginAttempt, "tentatives de connexion")
        finally:
            self._set_fk_checks(True)

    def _clear_media_dirs(self) -> None:
        media_root = Path(getattr(settings, "MEDIA_ROOT", "") or "")
        if not media_root.exists():
            self.stdout.write("Media : aucun dossier MEDIA_ROOT")
            return
        # Ne jamais toucher hors MEDIA_ROOT.
        candidates = [
            "students",
            "student",
            "guardians",
            "guardian",
            "cards",
            "card",
            "receipts",
            "receipt",
            "communications",
            "communication",
            "documents",
            "uploads",
            "photos",
        ]
        removed = 0
        for name in candidates:
            path = media_root / name
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                path.mkdir(parents=True, exist_ok=True)
                removed += 1
                self.stdout.write(f"  - media/{name} vidé")
        self.stdout.write(f"Media : {removed} dossier(s) nettoyé(s)")

    def _snapshot_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        try:
            from apps.secretariat.models import (
                AcademicYear,
                Enrollment,
                Guardian,
                SchoolClass,
                Student,
            )

            out["students"] = Student.objects.count()
            out["guardians"] = Guardian.objects.count()
            out["enrollments"] = Enrollment.objects.count()
            out["classes"] = SchoolClass.objects.count()
            out["years"] = AcademicYear.objects.count()
        except Exception:
            pass
        try:
            from apps.finance.models import Payment, SchoolFee

            out["payments"] = Payment.objects.count()
            out["fees"] = SchoolFee.objects.count()
        except Exception:
            pass
        try:
            from apps.discipline.models import DailyAttendance, DisciplinaryIncident

            out["attendances"] = DailyAttendance.objects.count()
            out["incidents"] = DisciplinaryIncident.objects.count()
        except Exception:
            pass
        return out
