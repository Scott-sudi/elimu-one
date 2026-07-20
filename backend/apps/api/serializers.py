"""API serializers."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog, LoginAttempt


class RoleSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Role
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_system",
            "is_active",
            "user_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    role_code = serializers.CharField(source="role.code", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "public_id",
            "username",
            "email",
            "nom",
            "postnom",
            "prenom",
            "full_name",
            "sexe",
            "telephone",
            "role",
            "role_code",
            "role_name",
            "is_active",
            "is_archived",
            "must_change_password",
            "last_login",
            "date_joined",
            "updated_at",
            "archived_at",
        ]
        read_only_fields = [
            "public_id",
            "is_archived",
            "last_login",
            "date_joined",
            "updated_at",
            "archived_at",
            "role_code",
            "role_name",
            "full_name",
        ]


class UserCreateSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=100)
    postnom = serializers.CharField(max_length=100, required=False, allow_blank=True)
    prenom = serializers.CharField(max_length=100)
    sexe = serializers.ChoiceField(choices=User.Gender.choices, required=False, allow_blank=True)
    telephone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    username = serializers.CharField(max_length=150)
    role_id = serializers.IntegerField()
    is_active = serializers.BooleanField(default=True)
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    must_change_password = serializers.BooleanField(default=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Les mots de passe ne correspondent pas."})
        validate_password(attrs["password"])
        if not Role.objects.filter(pk=attrs["role_id"], is_active=True).exists():
            raise serializers.ValidationError({"role_id": "Rôle invalide."})
        if User.objects.filter(username__iexact=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "Le nom d'utilisateur existe déjà."})
        return attrs


class UserUpdateSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=100)
    postnom = serializers.CharField(max_length=100, required=False, allow_blank=True)
    prenom = serializers.CharField(max_length=100)
    sexe = serializers.ChoiceField(choices=User.Gender.choices, required=False, allow_blank=True)
    telephone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    username = serializers.CharField(max_length=150)
    role_id = serializers.IntegerField()
    is_active = serializers.BooleanField(required=False)
    must_change_password = serializers.BooleanField(required=False)

    def validate_role_id(self, value):
        if not Role.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Rôle invalide.")
        return value


class PasswordResetSerializer(serializers.Serializer):
    temporary_password = serializers.CharField(write_only=True)
    temporary_password_confirm = serializers.CharField(write_only=True)
    must_change_password = serializers.BooleanField(default=True)

    def validate(self, attrs):
        if attrs["temporary_password"] != attrs["temporary_password_confirm"]:
            raise serializers.ValidationError(
                {"temporary_password_confirm": "Les mots de passe ne correspondent pas."}
            )
        validate_password(attrs["temporary_password"])
        return attrs


class StatusSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["activate", "deactivate", "archive"])


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Les mots de passe ne correspondent pas."}
            )
        validate_password(attrs["new_password"])
        return attrs


class SetupSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=100)
    postnom = serializers.CharField(max_length=100, required=False, allow_blank=True)
    prenom = serializers.CharField(max_length=100)
    telephone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Les mots de passe ne correspondent pas."})
        validate_password(attrs["password"])
        return attrs


class LoginAttemptSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = LoginAttempt
        fields = [
            "id",
            "user_name",
            "attempted_username",
            "success",
            "failure_reason",
            "ip_address",
            "browser",
            "device",
            "operating_system",
            "created_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user_id else ""


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor_name",
            "action",
            "entity_type",
            "entity_public_id",
            "description",
            "ip_address",
            "created_at",
        ]

    def get_actor_name(self, obj):
        return obj.actor.get_full_name() if obj.actor_id else "Système"
