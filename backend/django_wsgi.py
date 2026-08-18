"""o2switch / Passenger WSGI entry (NOT named passenger_wsgi.py).

cPanel generates its own passenger_wsgi.py and loads THIS file.
If Application startup file is also passenger_wsgi.py, Passenger recurses forever.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parent
STDERR_LOG = PROJECT_DIR / "stderr.log"
TMP_DIR = PROJECT_DIR / "tmp"


def _log(message: str) -> None:
    try:
        STDERR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with STDERR_LOG.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip() + "\n")
    except OSError:
        pass
    try:
        sys.stderr.write(message.rstrip() + "\n")
    except OSError:
        pass


def _ensure_dirs() -> None:
    for path in (TMP_DIR, PROJECT_DIR / "logs", PROJECT_DIR / "media", PROJECT_DIR / "staticfiles"):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _log(f"[django_wsgi] cannot create {path}: {exc}")


def _load_dotenv() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.is_file():
        alt = PROJECT_DIR / ".env"
        env_path = alt if alt.is_file() else env_path
    if not env_path.is_file():
        _log(f"[django_wsgi] WARNING: .env not found at {ROOT_DIR / '.env'}")
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
        _log(f"[django_wsgi] loaded .env via python-dotenv: {env_path}")
        return
    except ImportError:
        pass

    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            os.environ.setdefault(key, value)
        _log(f"[django_wsgi] loaded .env via builtin parser: {env_path}")
    except OSError as exc:
        _log(f"[django_wsgi] failed reading .env: {exc}")


def _bootstrap():
    if str(PROJECT_DIR) not in sys.path:
        sys.path.insert(0, str(PROJECT_DIR))

    _ensure_dirs()
    _load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

    from config.wsgi import application as app

    return app


try:
    application = _bootstrap()
except Exception:
    _log("[django_wsgi] FATAL import error:")
    _log(traceback.format_exc())
    raise
