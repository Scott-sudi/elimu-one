"""Account and authentication views."""

from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import TemplateView

from apps.accounts.forms import (
    ChangePasswordForm,
    LoginForm,
    PasswordResetForm,
    ProfileForm,
    SetupAdministratorForm,
    UserCreateForm,
    UserUpdateForm,
)
from apps.accounts.models import Role, SystemConfiguration, User
from apps.accounts.services import (
    AuthenticationError,
    authenticate_user,
    change_own_password,
    create_initial_administrator,
    create_staff_user,
    has_administrator,
    logout_user,
    reset_user_password,
    set_user_status,
    update_own_profile,
    update_staff_user,
)
from apps.core.mixins import AdministratorRequiredMixin
from apps.core.utils import api_response


def _wants_json(request: HttpRequest) -> bool:
    accept = request.headers.get("Accept", "")
    content_type = request.headers.get("Content-Type", "")
    return "application/json" in accept or "application/json" in content_type or request.headers.get("HX-Request") == "true" and request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json"


def _parse_body(request: HttpRequest) -> dict:
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return {}
    return request.POST.dict()


class SetupView(View):
    template_name = "setup/setup.html"

    def dispatch(self, request, *args, **kwargs):
        if has_administrator() or SystemConfiguration.is_setup_complete():
            return redirect("accounts:login")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {"form": SetupAdministratorForm()})

    def post(self, request):
        form = SetupAdministratorForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form}, status=400)
        try:
            create_initial_administrator(
                nom=form.cleaned_data["nom"],
                postnom=form.cleaned_data.get("postnom") or "",
                prenom=form.cleaned_data["prenom"],
                telephone=form.cleaned_data.get("telephone") or "",
                email=form.cleaned_data.get("email") or "",
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
                request=request,
            )
        except AuthenticationError as exc:
            form.add_error(None, exc.message)
            return render(request, self.template_name, {"form": form}, status=400)
        messages.success(request, "Configuration initiale terminée. Vous pouvez vous connecter.")
        return redirect("accounts:login")


class LoginView(View):
    template_name = "accounts/auth/login.html"

    def dispatch(self, request, *args, **kwargs):
        if not has_administrator() and not SystemConfiguration.is_setup_complete():
            return redirect("setup:setup")
        if request.user.is_authenticated and request.user.is_administrateur():
            return redirect("dashboard:home")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        data = _parse_body(request)
        form = LoginForm(data)
        wants_json = (
            "application/json" in request.headers.get("Accept", "")
            or "application/json" in (request.content_type or "")
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        )
        if not form.is_valid():
            if wants_json:
                return api_response(
                    success=False,
                    message="Veuillez vérifier les informations saisies.",
                    errors=form.errors,
                    status=400,
                )
            return render(request, self.template_name, {"form": form, "error": "Identifiants incorrects."}, status=400)
        try:
            authenticate_user(
                request=request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
        except AuthenticationError as exc:
            if wants_json:
                return api_response(success=False, message=exc.message, status=400)
            return render(request, self.template_name, {"form": form, "error": exc.message}, status=400)

        redirect_url = reverse("dashboard:home")
        if wants_json:
            return api_response(
                success=True,
                message="Connexion réussie.",
                data={"redirect_url": redirect_url},
            )
        return redirect(redirect_url)


@login_required
@require_POST
def logout_view(request):
    logout_user(request=request)
    return redirect("accounts:login")


class UserListView(AdministratorRequiredMixin, TemplateView):
    template_name = "accounts/users/list.html"
    partial_template = "accounts/users/_table.html"

    def get_queryset(self):
        qs = User.objects.select_related("role").all()
        search = self.request.GET.get("q", "").strip()
        role = self.request.GET.get("role", "").strip()
        status = self.request.GET.get("status", "").strip()

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
        if status == "active":
            qs = qs.filter(is_active=True, is_archived=False)
        elif status in {"inactive", "disabled"}:
            qs = qs.filter(is_active=False, is_archived=False)
        elif status == "archived":
            qs = qs.filter(is_archived=True)
        return qs.order_by("-date_joined")

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        paginator = Paginator(qs, 15)
        page_obj = paginator.get_page(request.GET.get("page"))
        context = {
            "page_obj": page_obj,
            "users": page_obj.object_list,
            "roles": Role.objects.filter(is_active=True),
            "filters": {
                "q": request.GET.get("q", ""),
                "role": request.GET.get("role", ""),
                "status": request.GET.get("status", ""),
            },
            "page_title": "Utilisateurs",
            "breadcrumb": [("Utilisateurs", None)],
        }
        if request.headers.get("HX-Request") == "true":
            return render(request, self.partial_template, context)
        return render(request, self.template_name, context)


class UserCreateView(AdministratorRequiredMixin, View):
    def get(self, request):
        form = UserCreateForm()
        return render(
            request,
            "accounts/users/_form.html",
            {"form": form, "mode": "create", "roles": Role.objects.filter(is_active=True)},
        )

    def post(self, request):
        data = _parse_body(request)
        # Normalize checkbox / role fields from HTML forms
        if "is_active" not in data:
            data["is_active"] = False
        elif data.get("is_active") in ("1", "true", "on", True):
            data["is_active"] = True
        if "must_change_password" in data:
            data["must_change_password"] = data.get("must_change_password") in ("1", "true", "on", True)
        form = UserCreateForm(data)
        if not form.is_valid():
            if request.headers.get("HX-Request") or "application/json" in request.headers.get("Accept", ""):
                return api_response(success=False, message="Formulaire invalide.", errors=form.errors, status=400)
            return render(
                request,
                "accounts/users/_form.html",
                {"form": form, "mode": "create", "roles": Role.objects.filter(is_active=True)},
                status=400,
            )
        try:
            user = create_staff_user(
                request=request,
                data={
                    **form.cleaned_data,
                    "password": form.cleaned_data["password"],
                },
            )
        except AuthenticationError as exc:
            return api_response(success=False, message=exc.message, status=400)
        return api_response(
            success=True,
            message="Utilisateur créé avec succès.",
            data={"public_id": str(user.public_id)},
        )


class UserDetailView(AdministratorRequiredMixin, View):
    def get(self, request, public_id):
        user = get_object_or_404(User.objects.select_related("role"), public_id=public_id)
        return render(request, "accounts/users/_details.html", {"user_obj": user})


class UserUpdateView(AdministratorRequiredMixin, View):
    def get(self, request, public_id):
        user = get_object_or_404(User.objects.select_related("role"), public_id=public_id)
        form = UserUpdateForm(
            initial={
                "nom": user.nom,
                "postnom": user.postnom,
                "prenom": user.prenom,
                "sexe": user.sexe,
                "telephone": user.telephone,
                "email": user.email,
                "username": user.username,
                "role_id": user.role_id,
                "is_active": user.is_active,
                "must_change_password": user.must_change_password,
            },
            user=user,
        )
        return render(
            request,
            "accounts/users/_form.html",
            {"form": form, "mode": "edit", "user_obj": user, "roles": Role.objects.filter(is_active=True)},
        )

    def post(self, request, public_id):
        user = get_object_or_404(User, public_id=public_id)
        data = _parse_body(request)
        form = UserUpdateForm(data, user=user)
        if not form.is_valid():
            return api_response(success=False, message="Formulaire invalide.", errors=form.errors, status=400)
        try:
            update_staff_user(request=request, user=user, data=form.cleaned_data)
        except AuthenticationError as exc:
            return api_response(success=False, message=exc.message, status=400)
        return api_response(success=True, message="Les modifications ont été enregistrées.")


class UserStatusView(AdministratorRequiredMixin, View):
    def post(self, request, public_id, action):
        user = get_object_or_404(User, public_id=public_id)
        if user.pk == request.user.pk and action in {"deactivate", "archive"}:
            return api_response(
                success=False,
                message="Vous ne pouvez pas désactiver ou archiver votre propre compte.",
                status=400,
            )
        try:
            set_user_status(request=request, user=user, action=action)
        except AuthenticationError as exc:
            return api_response(success=False, message=exc.message, status=400)
        messages_map = {
            "activate": "Le compte a été réactivé.",
            "deactivate": "Le compte a été désactivé.",
            "archive": "Le compte a été archivé.",
        }
        return api_response(success=True, message=messages_map.get(action, "Statut mis à jour."))


class UserPasswordResetView(AdministratorRequiredMixin, View):
    def get(self, request, public_id):
        user = get_object_or_404(User, public_id=public_id)
        form = PasswordResetForm()
        return render(
            request,
            "accounts/users/_form.html",
            {"form": form, "mode": "reset_password", "user_obj": user, "roles": Role.objects.filter(is_active=True)},
        )

    def post(self, request, public_id):
        user = get_object_or_404(User, public_id=public_id)
        data = _parse_body(request)
        form = PasswordResetForm(data)
        if not form.is_valid():
            return api_response(success=False, message="Formulaire invalide.", errors=form.errors, status=400)
        reset_user_password(
            request=request,
            user=user,
            temporary_password=form.cleaned_data["temporary_password"],
            force_change=form.cleaned_data.get("must_change_password", True),
        )
        return api_response(success=True, message="Le mot de passe temporaire a été réinitialisé.")


class RoleListView(AdministratorRequiredMixin, TemplateView):
    template_name = "accounts/roles/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        roles = Role.objects.annotate(user_count=Count("users")).order_by("name")
        permissions = [
            ("view_admin_dashboard", "Tableau de bord administrateur"),
            ("manage_users", "Gestion des utilisateurs"),
            ("view_login_history", "Consultation des connexions"),
            ("view_audit_log", "Consultation du journal"),
            ("manage_own_profile", "Gestion du profil"),
        ]
        context.update(
            {
                "roles": roles,
                "permissions": permissions,
                "page_title": "Rôles et permissions",
                "breadcrumb": [("Rôles et permissions", None)],
            }
        )
        return context


class ProfileView(AdministratorRequiredMixin, View):
    template_name = "accounts/profile/profile.html"

    def get(self, request):
        form = ProfileForm(initial={"telephone": request.user.telephone, "email": request.user.email})
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "page_title": "Mon profil",
                "breadcrumb": [("Mon profil", None)],
            },
        )

    def post(self, request):
        form = ProfileForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "page_title": "Mon profil",
                    "breadcrumb": [("Mon profil", None)],
                },
                status=400,
            )
        update_own_profile(
            request=request,
            user=request.user,
            telephone=form.cleaned_data.get("telephone") or "",
            email=form.cleaned_data.get("email") or "",
        )
        messages.success(request, "Les modifications ont été enregistrées.")
        return redirect("accounts:profile")


class ChangePasswordView(AdministratorRequiredMixin, View):
    template_name = "accounts/profile/change_password.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "form": ChangePasswordForm(),
                "forced": request.GET.get("forced") == "1",
                "page_title": "Changer le mot de passe",
                "breadcrumb": [("Mon profil", reverse("accounts:profile")), ("Mot de passe", None)],
            },
        )

    def post(self, request):
        form = ChangePasswordForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "forced": request.GET.get("forced") == "1",
                    "page_title": "Changer le mot de passe",
                    "breadcrumb": [("Mon profil", reverse("accounts:profile")), ("Mot de passe", None)],
                },
                status=400,
            )
        try:
            change_own_password(
                request=request,
                user=request.user,
                old_password=form.cleaned_data["old_password"],
                new_password=form.cleaned_data["new_password"],
            )
        except AuthenticationError as exc:
            form.add_error("old_password", exc.message)
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "forced": True,
                    "page_title": "Changer le mot de passe",
                    "breadcrumb": [("Mon profil", reverse("accounts:profile")), ("Mot de passe", None)],
                },
                status=400,
            )
        messages.success(request, "Mot de passe modifié avec succès.")
        return redirect("dashboard:home")
