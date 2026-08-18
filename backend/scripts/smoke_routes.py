"""Smoke-test GET routes for template/runtime errors (run from backend/)."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import URLPattern, URLResolver, get_resolver

from apps.accounts.models import Role
from apps.accounts.services import create_initial_administrator, create_staff_user, ensure_system_roles
from apps.secretariat.models import AcademicYear
from apps.secretariat.services.year_context import SESSION_KEY

if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]

User = get_user_model()

SKIP_PREFIXES = (
    "/admin/",
    "/api/v1/",
    "/media/",
    "/static/",
)

SKIP_NAMES = {
    "admin:index",
}


@dataclass
class RouteFailure:
    role: str
    path: str
    name: str
    status: int
    detail: str


def collect_patterns(resolver, prefix=""):
    routes = []
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLResolver):
            routes.extend(collect_patterns(pattern, prefix + str(pattern.pattern)))
        elif isinstance(pattern, URLPattern):
            full = prefix + str(pattern.pattern)
            routes.append((pattern.name or "", full))
    return routes


def fill_kwargs(path: str) -> str | None:
    """Replace path converters with dummy values; skip routes needing real FK rows."""
    out = path
    if "<uuid:" in out or "<str:" in out or "<int:" in out:
        out = re.sub(r"<uuid:[^>]+>", "00000000-0000-4000-8000-000000000001", out)
        out = re.sub(r"<str:[^>]+>", "demo-placeholder", out)
        out = re.sub(r"<int:[^>]+>", "1", out)
    if "demo-placeholder" in out and ("cards" in out or "qr" in out):
        return None
    return out


def ensure_users():
    ensure_system_roles()
    if not User.objects.filter(username="smoke.admin").exists():
        if not User.objects.filter(role__code=Role.CODE_ADMINISTRATEUR).exists():
            create_initial_administrator(
                nom="Smoke",
                postnom="",
                prenom="Admin",
                telephone="",
                email="",
                username="smoke.admin",
                password="SmokePass123!",
            )
        else:
            admin_role = Role.objects.get(code=Role.CODE_ADMINISTRATEUR)
            create_staff_user(
                request=None,
                data={
                    "nom": "Smoke",
                    "postnom": "",
                    "prenom": "Admin",
                    "username": "smoke.admin",
                    "password": "SmokePass123!",
                    "role_id": admin_role.id,
                    "is_active": True,
                },
            )
    role_map = {}
    for code in (
        Role.CODE_SECRETAIRE,
        Role.CODE_COMPTABLE,
        Role.CODE_DISCIPLINE,
        Role.CODE_PREFET,
    ):
        username = f"smoke.{code.lower()}"
        if User.objects.filter(username=username).exists():
            role_map[code] = User.objects.get(username=username)
            continue
        role = Role.objects.get(code=code)
        role_map[code] = create_staff_user(
            request=None,
            data={
                "nom": "Smoke",
                "postnom": "",
                "prenom": code.title(),
                "username": username,
                "password": "SmokePass123!",
                "role_id": role.id,
                "is_active": True,
            },
        )
    admin = User.objects.get(username="smoke.admin")
    return {
        "ADMIN": admin,
        Role.CODE_SECRETAIRE: role_map[Role.CODE_SECRETAIRE],
        Role.CODE_COMPTABLE: role_map[Role.CODE_COMPTABLE],
        Role.CODE_DISCIPLINE: role_map[Role.CODE_DISCIPLINE],
        Role.CODE_PREFET: role_map[Role.CODE_PREFET],
    }


def main() -> int:
    users = ensure_users()
    resolver = get_resolver()
    raw_routes = collect_patterns(resolver)
    failures: list[RouteFailure] = []
    route_count = 0

    for role_label, user in users.items():
        client = Client()
        client.force_login(user)
        if user.must_change_password:
            user.must_change_password = False
            user.save(update_fields=["must_change_password"])
        year = AcademicYear.objects.filter(is_closed=False).order_by("-start_date").first()
        if year is not None:
            session = client.session
            session[SESSION_KEY] = year.pk
            session.save()
        seen = set()
        for name, path in raw_routes:
            if name in SKIP_NAMES:
                continue
            filled = fill_kwargs(path)
            if filled is None or filled in seen:
                continue
            seen.add(filled)
            if any(filled.startswith(p) for p in SKIP_PREFIXES):
                continue
            try:
                response = client.get(filled, follow=False)
            except Exception as exc:  # noqa: BLE001 — smoke harness
                failures.append(RouteFailure(role_label, filled, name, 0, repr(exc)))
                continue
            if response.status_code >= 500:
                detail = getattr(response, "content", b"")[:300].decode("utf-8", errors="replace")
                failures.append(
                    RouteFailure(role_label, filled, name, response.status_code, detail)
                )
        route_count = max(route_count, len(seen))

    if failures:
        print(f"SMOKE FAILURES: {len(failures)}")
        for item in failures:
            print(f"- [{item.role}] {item.status} {item.path} ({item.name})")
            print(f"  {item.detail[:200]}")
        return 1

    print(f"SMOKE OK: {route_count} unique GET routes checked per role ({len(users)} roles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
