"""Administrator module tests."""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Role, SystemConfiguration, User
from apps.accounts.services import (
    AuthenticationError,
    authenticate_user,
    create_initial_administrator,
    create_staff_user,
    ensure_system_roles,
    reset_user_password,
    set_user_status,
)
from apps.audit.models import AuditLog, LoginAttempt


@pytest.fixture
def roles(db):
    return ensure_system_roles()


@pytest.fixture
def admin_user(roles):
    return create_initial_administrator(
        nom="Mbala",
        postnom="Jean",
        prenom="Patrick",
        telephone="0990000000",
        email="admin@kalunga.local",
        username="admin.kalunga",
        password="AdminPass123!",
    )


@pytest.mark.django_db
def test_system_roles_created(roles):
    assert Role.objects.count() >= 4
    assert Role.objects.filter(code="ADMINISTRATEUR", is_system=True).exists()


@pytest.mark.django_db
def test_create_initial_admin_and_block_second(roles):
    user = create_initial_administrator(
        nom="Test",
        postnom="",
        prenom="Admin",
        telephone="",
        email="",
        username="first.admin",
        password="AdminPass123!",
    )
    assert user.check_password("AdminPass123!")
    assert user.password != "AdminPass123!"
    assert SystemConfiguration.is_setup_complete()
    with pytest.raises(AuthenticationError):
        create_initial_administrator(
            nom="Autre",
            postnom="",
            prenom="Admin",
            telephone="",
            email="",
            username="second.admin",
            password="AdminPass123!",
        )


@pytest.mark.django_db
def test_setup_view_creates_admin(client, roles):
    url = reverse("setup:setup")
    response = client.post(
        url,
        {
            "nom": "Kalunga",
            "postnom": "",
            "prenom": "Admin",
            "telephone": "0812345678",
            "email": "setup@kalunga.local",
            "username": "setup.admin",
            "password": "SetupPass123!",
            "password_confirm": "SetupPass123!",
        },
    )
    assert response.status_code in (302, 200)
    assert User.objects.filter(username="setup.admin").exists()
    # Second setup blocked
    response2 = client.get(url)
    assert response2.status_code == 302


@pytest.mark.django_db
def test_login_success_and_failure(client, admin_user):
    url = reverse("accounts:login")
    bad = client.post(
        url,
        data='{"username":"admin.kalunga","password":"wrong"}',
        content_type="application/json",
        HTTP_ACCEPT="application/json",
    )
    assert bad.status_code == 400
    assert LoginAttempt.objects.filter(success=False).exists()

    good = client.post(
        url,
        data='{"username":"admin.kalunga","password":"AdminPass123!"}',
        content_type="application/json",
        HTTP_ACCEPT="application/json",
    )
    assert good.status_code == 200
    data = good.json()
    assert data["success"] is True


@pytest.mark.django_db
def test_lockout_after_failures(rf, admin_user, settings):
    settings.MAX_FAILED_LOGIN_ATTEMPTS = 5
    settings.ACCOUNT_LOCKOUT_MINUTES = 15
    request = rf.post("/connexion/")
    request.session = {}
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            authenticate_user(request=request, username="admin.kalunga", password="bad")
    admin_user.refresh_from_db()
    assert admin_user.is_locked()


@pytest.mark.django_db
def test_user_lifecycle(client, admin_user, roles):
    client.force_login(admin_user)
    secretaire = roles[Role.CODE_SECRETAIRE]
    user = create_staff_user(
        request=None,
        data={
            "username": "secretaire1",
            "password": "TempPass123!",
            "nom": "Nzuzi",
            "postnom": "",
            "prenom": "Marie",
            "email": "marie@kalunga.local",
            "telephone": "",
            "sexe": "F",
            "role_id": secretaire.id,
            "is_active": True,
            "must_change_password": True,
        },
    )
    assert User.objects.filter(username="secretaire1").exists()
    assert AuditLog.objects.filter(action=AuditLog.Action.USER_CREATED).exists()

    with pytest.raises(AuthenticationError):
        create_staff_user(
            request=None,
            data={
                "username": "secretaire1",
                "password": "TempPass123!",
                "nom": "Dup",
                "prenom": "Dup",
                "role_id": secretaire.id,
            },
        )

    set_user_status(request=None, user=user, action="deactivate")
    user.refresh_from_db()
    assert not user.is_active

    set_user_status(request=None, user=user, action="activate")
    user.refresh_from_db()
    assert user.is_active

    set_user_status(request=None, user=user, action="archive")
    user.refresh_from_db()
    assert user.is_archived

    reset_user_password(request=None, user=user, temporary_password="NewTemp123!")
    user.refresh_from_db()
    assert user.check_password("NewTemp123!")


@pytest.mark.django_db
def test_non_admin_cannot_login_web(rf, roles):
    role = roles[Role.CODE_SECRETAIRE]
    user = User.objects.create_user(
        username="sec.only",
        password="TempPass123!",
        nom="Sec",
        prenom="Only",
        role=role,
    )
    request = rf.post("/connexion/")
    request.session = {}
    with pytest.raises(AuthenticationError):
        authenticate_user(request=request, username="sec.only", password="TempPass123!")
    assert user.pk


@pytest.mark.django_db
def test_disabled_and_archived_cannot_login(rf, admin_user):
    request = rf.post("/connexion/")
    request.session = {}
    admin_user.deactivate()
    with pytest.raises(AuthenticationError):
        authenticate_user(request=request, username="admin.kalunga", password="AdminPass123!")
    admin_user.activate()
    admin_user.archive()
    with pytest.raises(AuthenticationError):
        authenticate_user(request=request, username="admin.kalunga", password="AdminPass123!")


@pytest.mark.django_db
def test_user_search_filter_pagination(client, admin_user, roles):
    client.force_login(admin_user)
    for i in range(16):
        create_staff_user(
            request=None,
            data={
                "username": f"user{i}",
                "password": "TempPass123!",
                "nom": f"Nom{i}",
                "prenom": f"Prenom{i}",
                "role_id": roles[Role.CODE_COMPTABLE].id,
            },
        )
    url = reverse("accounts:users")
    response = client.get(url, {"q": "Nom1", "role": "COMPTABLE"})
    assert response.status_code == 200
    response_page = client.get(url, {"page": 2})
    assert response_page.status_code == 200


@pytest.mark.django_db
def test_dashboard_requires_admin(client, admin_user, roles):
    url = reverse("dashboard:home")
    assert client.get(url).status_code in (302, 403)
    client.force_login(admin_user)
    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_api_health_and_jwt(admin_user):
    api = APIClient()
    health = api.get("/api/v1/health/")
    assert health.status_code == 200
    assert health.json()["success"] is True

    token = api.post(
        "/api/v1/auth/token/",
        {"username": "admin.kalunga", "password": "AdminPass123!"},
        format="json",
    )
    assert token.status_code == 200
    access = token.json()["data"]["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me = api.get("/api/v1/auth/me/")
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "admin.kalunga"

    dash = api.get("/api/v1/admin/dashboard/")
    assert dash.status_code == 200


@pytest.mark.django_db
def test_api_users_crud(admin_user, roles):
    api = APIClient()
    api.force_authenticate(user=admin_user)
    create = api.post(
        "/api/v1/users/",
        {
            "nom": "Api",
            "prenom": "User",
            "username": "api.user",
            "role_id": roles[Role.CODE_DISCIPLINE].id,
            "password": "TempPass123!",
            "password_confirm": "TempPass123!",
        },
        format="json",
    )
    assert create.status_code == 201
    public_id = create.json()["data"]["public_id"]
    detail = api.get(f"/api/v1/users/{public_id}/")
    assert detail.status_code == 200
    status_resp = api.patch(
        f"/api/v1/users/{public_id}/status/",
        {"action": "deactivate"},
        format="json",
    )
    assert status_resp.status_code == 200


@pytest.mark.django_db
def test_csrf_on_login_form(client, admin_user):
    url = reverse("accounts:login")
    page = client.get(url)
    assert page.status_code == 200
    assert "csrfmiddlewaretoken" in page.content.decode() or "csrf" in page.content.decode().lower()


@pytest.mark.django_db
def test_error_pages(client):
    assert client.get("/page-introuvable-xyz/").status_code == 404
