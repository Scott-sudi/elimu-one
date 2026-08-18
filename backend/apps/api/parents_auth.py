"""Parents mobile API — authentication bootstrap."""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.api.views import envelope
from apps.secretariat.services.exceptions import SecretariatError
from apps.secretariat.services.guardian_service import (
    assert_accepted_phone_format,
    find_guardian_by_phone,
)

CREDENTIALS_FAILURE_MESSAGE = (
    "Identifiants incorrects. Vérifiez le téléphone et le numéro "
    "d'identification, puis réessayez."
)


def normalize_identification_number(value: str) -> str:
    """Compare IDs without spaces / case differences."""
    return "".join((value or "").split()).casefold()


class ParentPhoneVerifyThrottle(AnonRateThrottle):
    """Limite les tentatives de vérification (énumération)."""

    scope = "parent_phone_verify"
    rate = "30/hour"


class ParentPhoneVerifySerializer(serializers.Serializer):
    telephone = serializers.CharField(max_length=30, trim_whitespace=True)
    numero_identification = serializers.CharField(
        max_length=100,
        trim_whitespace=True,
    )

    def validate_telephone(self, value: str) -> str:
        try:
            return assert_accepted_phone_format(value)
        except SecretariatError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_numero_identification(self, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError(
                "Indiquez votre numéro d'identification."
            )
        return cleaned


class ParentPhoneVerifyAPIView(APIView):
    """Vérifie téléphone + numéro d'identification d'un responsable actif.

    Les deux doivent correspondre pour ouvrir la session mobile parents.

    POST (JSON) est le contrat normal. GET (query) est accepté en secours
    tant que Tiger Protect o2switch bloque certains POST hors navigateur.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ParentPhoneVerifyThrottle]
    authentication_classes = []

    def post(self, request):
        return self._verify(request.data)

    def get(self, request):
        return self._verify(request.query_params)

    def _verify(self, payload):
        serializer = ParentPhoneVerifySerializer(data=payload)
        if not serializer.is_valid():
            return envelope(
                success=False,
                message="Identifiants invalides.",
                errors=serializer.errors,
                http_status=400,
            )

        telephone = serializer.validated_data["telephone"]
        submitted_id = normalize_identification_number(
            serializer.validated_data["numero_identification"]
        )
        guardian = find_guardian_by_phone(telephone)

        if guardian is None or not guardian.is_active or guardian.is_archived:
            return envelope(
                success=True,
                message=CREDENTIALS_FAILURE_MESSAGE,
                data={
                    "recognized": False,
                    "next_auth_step": "phone",
                },
            )

        stored_id = normalize_identification_number(guardian.numero_identification)
        if not stored_id or stored_id != submitted_id:
            return envelope(
                success=True,
                message=CREDENTIALS_FAILURE_MESSAGE,
                data={
                    "recognized": False,
                    "next_auth_step": "phone",
                },
            )

        display_name = " ".join(
            part for part in (guardian.prenom, guardian.nom) if part
        ).strip() or str(guardian)

        return envelope(
            message="Connexion autorisée.",
            data={
                "recognized": True,
                "guardian_public_id": str(guardian.public_id),
                "display_name": display_name,
                "email": (guardian.email or "").strip(),
                "next_auth_step": "password",
                "available_auth_methods": [
                    "password",
                    "pin",
                    "otp",
                    "biometric",
                ],
            },
        )
