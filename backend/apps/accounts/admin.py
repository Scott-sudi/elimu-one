from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import Role, SystemConfiguration, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_system", "is_active", "updated_at")
    search_fields = ("code", "name")
    list_filter = ("is_system", "is_active")
    readonly_fields = ("created_at", "updated_at")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username",
        "nom",
        "prenom",
        "role",
        "is_active",
        "is_archived",
        "last_login",
    )
    list_filter = ("role", "is_active", "is_archived", "must_change_password")
    search_fields = ("username", "nom", "prenom", "email", "telephone", "public_id")
    ordering = ("nom", "prenom")
    readonly_fields = ("public_id", "date_joined", "updated_at", "last_login", "archived_at")

    fieldsets = (
        (None, {"fields": ("username", "password", "public_id")}),
        (
            "Identité",
            {"fields": ("nom", "postnom", "prenom", "sexe", "email", "telephone", "role")},
        ),
        (
            "Statut",
            {
                "fields": (
                    "is_active",
                    "is_archived",
                    "must_change_password",
                    "failed_login_attempts",
                    "locked_until",
                    "archived_at",
                )
            },
        ),
        ("Permissions Django", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "nom",
                    "prenom",
                    "role",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "updated_at")
