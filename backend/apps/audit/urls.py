from django.urls import path

from apps.audit.views import AuditLogView, LoginHistoryView

app_name = "audit"

urlpatterns = [
    path("connexions/", LoginHistoryView.as_view(), name="logins"),
    path("journal/", AuditLogView.as_view(), name="actions"),
]
