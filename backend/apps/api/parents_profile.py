"""Parents mobile API — profil responsable (lecture)."""

from __future__ import annotations

from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.api.views import envelope
from apps.secretariat.models import Guardian


class ParentProfileThrottle(AnonRateThrottle):
    scope = "parent_profile"
    rate = "120/hour"


def _display_name(guardian: Guardian) -> str:
    return " ".join(
        part for part in (guardian.prenom, guardian.nom) if part
    ).strip() or str(guardian)


def build_parent_profile(guardian: Guardian) -> dict:
    sexe_label = ""
    if guardian.sexe:
        sexe_label = dict(Guardian.Gender.choices).get(guardian.sexe, guardian.sexe)
    return {
        "guardian_public_id": str(guardian.public_id),
        "display_name": _display_name(guardian),
        "prenom": (guardian.prenom or "").strip(),
        "nom": (guardian.nom or "").strip(),
        "postnom": (guardian.postnom or "").strip(),
        "sexe": sexe_label,
        "telephone": (guardian.telephone_principal or "").strip(),
        "telephone_secondaire": (guardian.telephone_secondaire or "").strip(),
        "email": (guardian.email or "").strip(),
        "adresse": (guardian.adresse or "").strip(),
        "profession": (guardian.profession or "").strip(),
        "numero_identification": (guardian.numero_identification or "").strip(),
    }


class ParentProfileAPIView(APIView):
    """Fiche identité du responsable connecté (lecture seule)."""

    permission_classes = [AllowAny]
    throttle_classes = [ParentProfileThrottle]
    authentication_classes = []

    def get(self, request):
        guardian_id = (
            request.query_params.get("guardian_public_id")
            or request.headers.get("X-Guardian-Public-Id")
            or ""
        ).strip()
        if not guardian_id:
            return envelope(
                success=False,
                message="Identifiant responsable manquant.",
                errors={"guardian_public_id": ["Requis."]},
                http_status=400,
            )

        guardian = Guardian.objects.filter(
            public_id=guardian_id,
            is_archived=False,
            is_active=True,
        ).first()
        if guardian is None:
            return envelope(
                success=False,
                message="Responsable introuvable.",
                http_status=404,
            )

        return envelope(
            message="Profil responsable.",
            data=build_parent_profile(guardian),
        )
