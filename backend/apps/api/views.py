"""REST API views for version 1."""

from __future__ import annotations

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import Role, SystemConfiguration, User
from apps.accounts.services import (
    AuthenticationError,
    change_own_password,
    create_initial_administrator,
    create_staff_user,
    has_administrator,
    reset_user_password,
    set_user_status,
    update_staff_user,
)
from apps.api.permissions import IsAdministrator
from apps.api.serializers import (
    AuditLogSerializer,
    ChangePasswordSerializer,
    LoginAttemptSerializer,
    PasswordResetSerializer,
    RoleSerializer,
    SetupSerializer,
    StatusSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.audit.models import AuditLog, LoginAttempt


def envelope(success=True, message="", data=None, errors=None, http_status=200):
    return Response(
        {
            "success": success,
            "message": message,
            "data": data if data is not None else {},
            "errors": errors if errors is not None else {},
        },
        status=http_status,
    )


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return envelope(
            message="Service opérationnel.",
            data={"status": "ok", "time": timezone.now().isoformat()},
        )


class SetupStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return envelope(
            data={
                "initialized": has_administrator() or SystemConfiguration.is_setup_complete(),
            }
        )


class SetupInitializeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        payload.pop("password_confirm", None)
        try:
            user = create_initial_administrator(request=request, **payload)
        except AuthenticationError as exc:
            return envelope(success=False, message=exc.message, http_status=400)
        return envelope(
            message="Configuration initiale terminée.",
            data={"public_id": str(user.public_id), "username": user.username},
            http_status=201,
        )


class KalungaTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return envelope(message="Jeton délivré.", data=response.data)
        return envelope(
            success=False,
            message="Authentification échouée.",
            errors=response.data,
            http_status=response.status_code,
        )


class KalungaTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return envelope(message="Jeton rafraîchi.", data=response.data)
        return envelope(
            success=False,
            message="Rafraîchissement impossible.",
            errors=response.data,
            http_status=response.status_code,
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Client-side token discard for Flutter; server-side blacklist
        # can be enabled later when MySQL index constraints allow it.
        return envelope(message="Déconnexion effectuée.")


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return envelope(data=UserSerializer(request.user).data)


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            change_own_password(
                request=request,
                user=request.user,
                old_password=serializer.validated_data["old_password"],
                new_password=serializer.validated_data["new_password"],
            )
        except AuthenticationError as exc:
            return envelope(success=False, message=exc.message, http_status=400)
        return envelope(message="Mot de passe modifié avec succès.")


class DashboardAPIView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        users = User.objects.all()
        role_counts = {
            row["role__code"]: row["total"]
            for row in users.values("role__code").annotate(total=Count("id"))
        }
        return envelope(
            data={
                "total_users": users.count(),
                "active_users": users.filter(is_active=True, is_archived=False).count(),
                "inactive_users": users.filter(is_active=False, is_archived=False).count(),
                "administrators": role_counts.get(Role.CODE_ADMINISTRATEUR, 0),
                "secretaries": role_counts.get(Role.CODE_SECRETAIRE, 0),
                "accountants": role_counts.get(Role.CODE_COMPTABLE, 0),
                "discipline": role_counts.get(Role.CODE_DISCIPLINE, 0),
            }
        )


class UserViewSet(ModelViewSet):
    permission_classes = [IsAdministrator]
    lookup_field = "public_id"
    queryset = User.objects.select_related("role").all()
    serializer_class = UserSerializer

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        search = request.query_params.get("q", "").strip()
        role = request.query_params.get("role", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        if search:
            qs = qs.filter(
                Q(nom__icontains=search)
                | Q(postnom__icontains=search)
                | Q(prenom__icontains=search)
                | Q(username__icontains=search)
                | Q(telephone__icontains=search)
                | Q(email__icontains=search)
            )
        if role:
            qs = qs.filter(role__code=role)
        if status_filter == "active":
            qs = qs.filter(is_active=True, is_archived=False)
        elif status_filter == "inactive":
            qs = qs.filter(is_active=False, is_archived=False)
        elif status_filter == "archived":
            qs = qs.filter(is_archived=True)
        page = self.paginate_queryset(qs.order_by("-date_joined"))
        serializer = UserSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        payload.pop("password_confirm", None)
        try:
            user = create_staff_user(request=request, data=payload)
        except AuthenticationError as exc:
            return envelope(success=False, message=exc.message, http_status=400)
        return envelope(
            message="Utilisateur créé avec succès.",
            data=UserSerializer(user).data,
            http_status=201,
        )

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        return envelope(data=UserSerializer(user).data)

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            update_staff_user(request=request, user=user, data=serializer.validated_data)
        except AuthenticationError as exc:
            return envelope(success=False, message=exc.message, http_status=400)
        return envelope(message="Les modifications ont été enregistrées.", data=UserSerializer(user).data)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.pk == request.user.pk:
            return envelope(success=False, message="Vous ne pouvez pas archiver votre propre compte.", http_status=400)
        set_user_status(request=request, user=user, action="archive")
        return envelope(message="Le compte a été archivé.")


class UserStatusAPIView(APIView):
    permission_classes = [IsAdministrator]

    def patch(self, request, public_id):
        user = User.objects.filter(public_id=public_id).first()
        if not user:
            return envelope(success=False, message="Utilisateur introuvable.", http_status=404)
        serializer = StatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if user.pk == request.user.pk and serializer.validated_data["action"] in {"deactivate", "archive"}:
            return envelope(
                success=False,
                message="Vous ne pouvez pas désactiver ou archiver votre propre compte.",
                http_status=400,
            )
        set_user_status(request=request, user=user, action=serializer.validated_data["action"])
        return envelope(message="Statut mis à jour.", data=UserSerializer(user).data)


class UserResetPasswordAPIView(APIView):
    permission_classes = [IsAdministrator]

    def post(self, request, public_id):
        user = User.objects.filter(public_id=public_id).first()
        if not user:
            return envelope(success=False, message="Utilisateur introuvable.", http_status=404)
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_user_password(
            request=request,
            user=user,
            temporary_password=serializer.validated_data["temporary_password"],
            force_change=serializer.validated_data.get("must_change_password", True),
        )
        return envelope(message="Le mot de passe temporaire a été réinitialisé.")


class RoleViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAdministrator]
    queryset = Role.objects.annotate(user_count=Count("users")).order_by("name")
    serializer_class = RoleSerializer

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return envelope(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return envelope(data=self.get_serializer(self.get_object()).data)


class LoginAttemptViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAdministrator]
    queryset = LoginAttempt.objects.select_related("user").all()
    serializer_class = LoginAttemptSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset().order_by("-created_at")
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class AuditLogViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAdministrator]
    queryset = AuditLog.objects.select_related("actor").all()
    serializer_class = AuditLogSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset().order_by("-created_at")
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
