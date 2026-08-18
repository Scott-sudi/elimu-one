"""API enregistrement des jetons push (FCM) parents."""

from __future__ import annotations

from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.api.models import ParentPushDevice
from apps.api.views import envelope
from apps.secretariat.models import Guardian


class ParentDeviceRegisterThrottle(AnonRateThrottle):
    scope = "parent_device_register"
    rate = "60/hour"


class ParentDeviceRegisterAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ParentDeviceRegisterThrottle]
    authentication_classes = []

    def post(self, request):
        guardian_id = (
            request.data.get("guardian_public_id")
            or request.headers.get("X-Guardian-Public-Id")
            or ""
        ).strip()
        token = (request.data.get("token") or "").strip()
        platform = (request.data.get("platform") or "android").strip().lower()

        if not guardian_id or not token:
            return envelope(
                success=False,
                message="guardian_public_id et token requis.",
                http_status=400,
            )
        if len(token) < 20:
            return envelope(
                success=False,
                message="Jeton appareil invalide.",
                http_status=400,
            )
        if platform not in {
            ParentPushDevice.Platform.ANDROID,
            ParentPushDevice.Platform.IOS,
            ParentPushDevice.Platform.WEB,
        }:
            platform = ParentPushDevice.Platform.ANDROID

        guardian = Guardian.objects.filter(
            public_id=guardian_id,
            is_active=True,
            is_archived=False,
        ).first()
        if guardian is None:
            return envelope(
                success=False,
                message="Compte parent introuvable.",
                http_status=404,
            )

        device, _created = ParentPushDevice.objects.update_or_create(
            token=token,
            defaults={
                "guardian": guardian,
                "platform": platform,
                "is_active": True,
            },
        )
        return envelope(
            message="Appareil enregistré.",
            data={
                "id": device.pk,
                "platform": device.platform,
                "is_active": device.is_active,
            },
        )
