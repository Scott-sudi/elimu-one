"""Administrator dashboard views."""

from django.db.models import Count, Q
from django.views.generic import TemplateView

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog, LoginAttempt
from apps.core.mixins import AdministratorRequiredMixin


class DashboardView(AdministratorRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = User.objects.select_related("role")
        role_counts = {
            row["role__code"]: row["total"]
            for row in users.values("role__code").annotate(total=Count("id"))
        }
        context.update(
            {
                "page_title": "Tableau de bord",
                "breadcrumb": [("Tableau de bord", None)],
                "stats": {
                    "total_users": users.count(),
                    "active_users": users.filter(is_active=True, is_archived=False).count(),
                    "inactive_users": users.filter(is_active=False, is_archived=False).count(),
                    "administrators": role_counts.get(Role.CODE_ADMINISTRATEUR, 0),
                    "secretaries": role_counts.get(Role.CODE_SECRETAIRE, 0),
                    "accountants": role_counts.get(Role.CODE_COMPTABLE, 0),
                    "discipline": role_counts.get(Role.CODE_DISCIPLINE, 0),
                },
                "recent_users": users.order_by("-date_joined")[:8],
                "recent_logins": LoginAttempt.objects.select_related("user").order_by("-created_at")[:8],
                "recent_actions": AuditLog.objects.select_related("actor").order_by("-created_at")[:8],
                "recently_deactivated": users.filter(is_active=False, is_archived=False).order_by("-updated_at")[:8],
            }
        )
        return context
