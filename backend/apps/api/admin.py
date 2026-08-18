from django.contrib import admin

from apps.api.models import ParentPushDevice


@admin.register(ParentPushDevice)
class ParentPushDeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "guardian", "platform", "is_active", "updated_at")
    list_filter = ("platform", "is_active")
    search_fields = ("token", "guardian__nom", "guardian__prenom", "guardian__telephone_principal")
    readonly_fields = ("created_at", "updated_at")
