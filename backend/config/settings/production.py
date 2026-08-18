"""Production settings."""

from pathlib import Path

from .base import *  # noqa: F403
from .base import build_databases
from .origins import trusted_origins_from_hosts

DEBUG = False

# Hébergement : MySQL par défaut (SQLite reste possible si DB_ENGINE=sqlite3).
DATABASES = build_databases(default_engine="django.db.backends.mysql")

# Always include http+https for every ALLOWED_HOST (covers *.odns.fr and future domaines).
CSRF_TRUSTED_ORIGINS = trusted_origins_from_hosts(  # noqa: F405
    ALLOWED_HOSTS,  # noqa: F405
    extra=env.list("CSRF_TRUSTED_ORIGINS", default=[]),  # noqa: F405
)
CORS_ALLOWED_ORIGINS = trusted_origins_from_hosts(  # noqa: F405
    ALLOWED_HOSTS,  # noqa: F405
    extra=env.list("CORS_ALLOWED_ORIGINS", default=[]),  # noqa: F405
)

# Defaults False until AutoSSL is confirmed. HTTP *.odns.fr cannot use Secure cookies.
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)  # noqa: F405
SESSION_COOKIE_SECURE = env.bool(  # noqa: F405
    "DJANGO_SESSION_COOKIE_SECURE",
    default=SECURE_SSL_REDIRECT,
)
CSRF_COOKIE_SECURE = env.bool(  # noqa: F405
    "DJANGO_CSRF_COOKIE_SECURE",
    default=SECURE_SSL_REDIRECT,
)

# Apache on o2switch often sends X-Forwarded-Proto: https even on HTTP.
# Django then treats the request as HTTPS → CSRF cookie not sent → 403 on every form.
# Trust the proxy header only when we actually force HTTPS.
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if SECURE_SSL_REDIRECT else None
)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=0)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)  # noqa: F405
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)  # noqa: F405

# Never allow all CORS origins in production
CORS_ALLOW_ALL_ORIGINS = False

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
)

# GZipMiddleware + Phusion Passenger (o2switch) can yield
# "Incomplete response received from application". Keep gzip off in production.
MIDDLEWARE = [  # noqa: F405
    m for m in MIDDLEWARE if m != "django.middleware.gzip.GZipMiddleware"  # noqa: F405
]

# Manifest storage raises hard 500 if any hashed static file is missing after deploy.
# Compressed (non-manifest) is safer on shared hosting until assets are fully synced.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

LOG_DIR = Path(env("DJANGO_LOG_DIR", default=BASE_DIR / "logs"))  # noqa: F405
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    # Prefer starting the app over crashing Passenger if logs are not writable.
    LOG_DIR = BASE_DIR / "logs"  # noqa: F405
    LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {process} {thread} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "django_file": {
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "django.log"),
            "formatter": "verbose",
        },
        "error_file": {
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "error.log"),
            "formatter": "verbose",
            "level": "ERROR",
        },
        "security_file": {
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "security.log"),
            "formatter": "verbose",
            "level": "WARNING",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "django_file", "error_file"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),  # noqa: F405
            "propagate": True,
        },
        "django.security": {
            "handlers": ["console", "security_file", "error_file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
