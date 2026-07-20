"""Audit web views."""

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.views.generic import TemplateView

from apps.audit.models import AuditLog, LoginAttempt
from apps.core.mixins import AdministratorRequiredMixin


class LoginHistoryView(AdministratorRequiredMixin, TemplateView):
    template_name = "audit/logins.html"
    partial_template = "audit/_logins_table.html"

    def get_queryset(self):
        qs = LoginAttempt.objects.select_related("user", "user__role").all()
        username = self.request.GET.get("user", "").strip()
        status = self.request.GET.get("status", "").strip()
        ip = self.request.GET.get("ip", "").strip()
        browser = self.request.GET.get("browser", "").strip()
        date_from = self.request.GET.get("date_from", "").strip()
        date_to = self.request.GET.get("date_to", "").strip()

        if username:
            qs = qs.filter(
                Q(attempted_username__icontains=username)
                | Q(user__username__icontains=username)
                | Q(user__nom__icontains=username)
            )
        if status == "success":
            qs = qs.filter(success=True)
        elif status == "failure":
            qs = qs.filter(success=False)
        if ip:
            qs = qs.filter(ip_address__icontains=ip)
        if browser:
            qs = qs.filter(browser__icontains=browser)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs.order_by("-created_at")

    def get(self, request, *args, **kwargs):
        page_obj = Paginator(self.get_queryset(), 20).get_page(request.GET.get("page"))
        context = {
            "page_obj": page_obj,
            "logins": page_obj.object_list,
            "filters": {
                "user": request.GET.get("user", ""),
                "status": request.GET.get("status", ""),
                "ip": request.GET.get("ip", ""),
                "browser": request.GET.get("browser", ""),
                "date_from": request.GET.get("date_from", ""),
                "date_to": request.GET.get("date_to", ""),
            },
            "page_title": "Connexions",
            "breadcrumb": [("Connexions", None)],
        }
        if request.headers.get("HX-Request") == "true":
            return render(request, self.partial_template, context)
        return render(request, self.template_name, context)


class AuditLogView(AdministratorRequiredMixin, TemplateView):
    template_name = "audit/actions.html"
    partial_template = "audit/_actions_table.html"

    def get_queryset(self):
        qs = AuditLog.objects.select_related("actor").all()
        actor = self.request.GET.get("actor", "").strip()
        action = self.request.GET.get("action", "").strip()
        entity = self.request.GET.get("entity", "").strip()
        date_from = self.request.GET.get("date_from", "").strip()
        date_to = self.request.GET.get("date_to", "").strip()

        if actor:
            qs = qs.filter(
                Q(actor__username__icontains=actor)
                | Q(actor__nom__icontains=actor)
                | Q(actor__prenom__icontains=actor)
            )
        if action:
            qs = qs.filter(action=action)
        if entity:
            qs = qs.filter(entity_type__icontains=entity)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs.order_by("-created_at")

    def get(self, request, *args, **kwargs):
        page_obj = Paginator(self.get_queryset(), 20).get_page(request.GET.get("page"))
        context = {
            "page_obj": page_obj,
            "actions": page_obj.object_list,
            "action_choices": AuditLog.Action.choices,
            "filters": {
                "actor": request.GET.get("actor", ""),
                "action": request.GET.get("action", ""),
                "entity": request.GET.get("entity", ""),
                "date_from": request.GET.get("date_from", ""),
                "date_to": request.GET.get("date_to", ""),
            },
            "page_title": "Journal d'activités",
            "breadcrumb": [("Journal d'activités", None)],
        }
        if request.headers.get("HX-Request") == "true":
            return render(request, self.partial_template, context)
        return render(request, self.template_name, context)
