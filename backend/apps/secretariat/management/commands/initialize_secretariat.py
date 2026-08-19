"""Initialize reference data required by secretariat services."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.secretariat.models import DocumentType, SecretariatSetting

DOCUMENT_TYPES = (
    ("ACTE_NAISSANCE", "Acte de naissance", True),
    ("BULLETIN", "Bulletin scolaire", True),
    ("PHOTO_IDENTITE", "Photo d'identité", True),
    ("CERTIFICAT_MEDICAL", "Certificat médical", False),
    ("ATTESTATION_TRANSFERT", "Attestation de transfert", False),
)

SETTINGS = (
    ("MATRICULE_PREFIX", "ELM", "Préfixe des matricules"),
    ("MATRICULE_PADDING", "5", "Longueur du compteur matricule"),
    ("ENROLLMENT_NUMBER_PREFIX", "INS", "Préfixe des numéros d'inscription"),
)


class Command(BaseCommand):
    help = "Initialise les paramètres et types de documents du secrétariat."

    @transaction.atomic
    def handle(self, *args, **options):
        for code, name, required in DOCUMENT_TYPES:
            DocumentType.objects.update_or_create(
                code=code,
                defaults={"name": name, "is_required": required, "is_active": True},
            )
        for key, value, description in SETTINGS:
            SecretariatSetting.objects.update_or_create(
                key=key,
                defaults={"value": value, "description": description, "is_active": True},
            )
        self.stdout.write(self.style.SUCCESS("Secrétariat initialisé avec succès."))
