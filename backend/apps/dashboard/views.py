"""Administrator dashboard views."""

from django.db.models import Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog, LoginAttempt


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and user.is_secretaire():
            return redirect("secretariat:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        if self.request.user.is_administrateur():
            return [self.template_name]
        return ["workspaces/home.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_administrateur():
            context.update(
                {
                    "page_title": "Mon espace de travail",
                    "breadcrumb": [("Mon espace de travail", None)],
                }
            )
            return context

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
