"""Tests for PREFET role seed, access control, and redirects."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.accounts.services import ensure_system_roles
from apps.secretariat.services.academic_service import create_academic_year
from apps.secretariat.services.year_context import SESSION_KEY
from datetime import date


@pytest.fixture
def roles(db):
    return ensure_system_roles()


@pytest.fixture
def prefet(roles):
    return User.objects.create_user(
        username="prefet_role_test",
        password="TempPass123!",
        nom="Mwamba",
        prenom="Jean",
        role=roles[Role.CODE_PREFET],
    )


@pytest.fixture
def accountant(roles):
    return User.objects.create_user(
        username="comptable_role_test",
        password="TempPass123!",
        nom="Ilunga",
        prenom="Claire",
        role=roles[Role.CODE_COMPTABLE],
    )


@pytest.mark.django_db
def test_prefet_role_seeded_once(roles):
    first = Role.objects.filter(code=Role.CODE_PREFET).count()
    ensure_system_roles()
    second = Role.objects.filter(code=Role.CODE_PREFET).count()
    assert first == 1
    assert second == 1
    role = Role.objects.get(code=Role.CODE_PREFET)
    assert role.is_system is True
    assert role.name == "Préfet"


@pytest.mark.django_db
def test_prefet_user_helper(prefet):
    assert prefet.is_prefet() is True
    assert prefet.is_comptable() is False
    assert prefet.role_code == Role.CODE_PREFET


@pytest.mark.django_db
def test_prefet_bi_overview_requires_year(client, prefet):
    client.force_login(prefet)
    response = client.get(reverse("bi:overview"))
    assert response.status_code == 302
    assert reverse("secretariat:academic-year-select") in response.url


@pytest.mark.django_db
def test_prefet_bi_overview_ok_with_year(client, prefet, db):
    year = create_academic_year(
        label="2025-2026-ROLE",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_active=True,
    )
    session = client.session
    session[SESSION_KEY] = year.pk
    session.save()
    client.force_login(prefet)
    response = client.get(reverse("bi:overview"))
    assert response.status_code == 200
    assert b"Vue" in response.content or b"effectif" in response.content.lower()


@pytest.mark.django_db
def test_accountant_cannot_access_bi(client, accountant, db):
    year = create_academic_year(
        label="2025-2026-ACC",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 7, 31),
        is_active=True,
    )
    session = client.session
    session[SESSION_KEY] = year.pk
    session.save()
    client.force_login(accountant)
    response = client.get(reverse("bi:overview"))
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_dashboard_redirects_prefet_to_year_or_bi(client, prefet):
    client.force_login(prefet)
    response = client.get(reverse("dashboard:home"))
    assert response.status_code == 302
    assert reverse("secretariat:academic-year-select") in response.url or reverse("bi:overview") in response.url
