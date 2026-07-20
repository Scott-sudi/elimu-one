"""Vite manifest helpers for Django templates."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.safestring import mark_safe


@lru_cache(maxsize=1)
def _load_manifest() -> dict:
    manifest_path = Path(settings.BASE_DIR) / "static" / "dist" / ".vite" / "manifest.json"
    if not manifest_path.exists():
        manifest_path = Path(settings.BASE_DIR) / "static" / "dist" / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def vite_asset_tags(entry: str = "backend/static/src/js/app.js") -> str:
    """Return link/script tags for a Vite entry, or empty string if missing."""
    manifest = _load_manifest()
    item = manifest.get(entry)
    if not item:
        # Try alternate keys
        for key, value in manifest.items():
            if key.endswith("app.js") or key.endswith("/app.js"):
                item = value
                break
    if not item:
        return ""

    tags: list[str] = []
    css_files = item.get("css") or []
    for css in css_files:
        url = staticfiles_storage.url(css.replace("assets/", "assets/", 1) if False else css)
        # Files are emitted under static/dist/; STATICFILES_DIRS includes dist root
        tags.append(f'<link rel="stylesheet" href="/static/{css}">')
    file_path = item.get("file")
    if file_path:
        tags.append(f'<script type="module" src="/static/{file_path}"></script>')
    return mark_safe("\n".join(tags))
