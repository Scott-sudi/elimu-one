from django.contrib import admin

from apps.audit.models import AuditLog, LoginAttempt


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("attempted_username", "success", "ip_address", "browser", "created_at")
    list_filter = ("success", "browser", "operating_system")
    search_fields = ("attempted_username", "ip_address", "user__username")
    readonly_fields = [f.name for f in LoginAttempt._meta.fields]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "entity_type", "ip_address", "created_at")
    list_filter = ("action", "entity_type")
    search_fields = ("description", "entity_public_id", "actor__username")
    readonly_fields = [f.name for f in AuditLog._meta.fields]
