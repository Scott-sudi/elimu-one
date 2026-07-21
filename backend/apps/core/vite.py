"""Vite manifest helpers for Django templates."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.utils.safestring import mark_safe


def _manifest_path() -> Path:
    base = Path(settings.BASE_DIR) / "static" / "dist"
    primary = base / ".vite" / "manifest.json"
    if primary.exists():
        return primary
    return base / "manifest.json"


def _load_manifest() -> dict:
    path = _manifest_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def vite_asset_tags(entry: str = "backend/static/src/js/app.js") -> str:
    """Return link/script tags for a Vite entry, or empty string if missing."""
    manifest = _load_manifest()
    item = manifest.get(entry)
    if not item:
        for key, value in manifest.items():
            if key.endswith("app.js") or key.endswith("/app.js"):
                item = value
                break
    if not item:
        return ""

    tags: list[str] = []
    for css in item.get("css") or []:
        tags.append(f'<link rel="stylesheet" href="/static/{css}?v={Path(css).stem}">')
    file_path = item.get("file")
    if file_path:
        tags.append(f'<script type="module" src="/static/{file_path}?v={Path(file_path).stem}"></script>')
    return mark_safe("\n".join(tags))
