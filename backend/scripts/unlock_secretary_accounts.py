"""One-shot helper: release forced password change for active secretaries."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from apps.accounts.models import Role, User  # noqa: E402


def main() -> None:
    qs = User.objects.filter(
        role__code=Role.CODE_SECRETAIRE,
        is_archived=False,
        must_change_password=True,
    )
    usernames = list(qs.values_list("username", flat=True))
    updated = qs.update(must_change_password=False)
    print(f"comptes_debloques={updated}")
    for username in usernames:
        print(f" - {username}")


if __name__ == "__main__":
    main()
