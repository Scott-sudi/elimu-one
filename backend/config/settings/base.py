"""Base settings shared by all environments."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    MAX_FAILED_LOGIN_ATTEMPTS=(int, 5),
    ACCOUNT_LOCKOUT_MINUTES=(int, 15),
    JWT_ACCESS_MINUTES=(int, 15),
    JWT_REFRESH_DAYS=(int, 7),
)

environ.Env.read_env(ROOT_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        "127.0.0.1",
        "localhost",
    ],
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    # Local apps
    "apps.core",
    "apps.accounts",
    "apps.dashboard",
    "apps.audit",
    "apps.api",
    "apps.secretariat",
    "apps.finance",
    "apps.discipline",
    "apps.bi",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.MustChangePasswordMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "builtins": [
                "apps.core.templatetags.kalunga_filters",
            ],
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.school_context",
                "apps.core.context_processors.secretariat_year_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


def _sqlite_name(raw_name: str) -> str:
    """Resolve a SQLite file path; accept a bare name, a path, or :memory:."""
    value = (raw_name or "").strip()
    if not value or value == ":memory:":
        return value or str(BASE_DIR / "db.sqlite3")
    path = Path(value)
    if path.suffix.lower() in {".sqlite", ".sqlite3", ".db"}:
        return str(path if path.is_absolute() else BASE_DIR / path)
    if "/" in value or "\\" in value:
        return str(path if path.is_absolute() else BASE_DIR / path)
    return str(BASE_DIR / f"{value}.sqlite3")


def build_databases(*, default_engine: str) -> dict:
    """SQLite locally, MySQL (or MariaDB) when DB_ENGINE says so."""
    engine = env("DB_ENGINE", default=default_engine).strip()
    backend = engine.lower().replace("django.db.backends.", "")
    if backend in {"sqlite", "sqlite3"}:
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": _sqlite_name(env("DB_NAME", default=str(BASE_DIR / "db.sqlite3"))),
            }
        }
    return {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("DB_NAME", default="elimu_school"),
            "USER": env("DB_USER", default="root"),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default="127.0.0.1"),
            "PORT": env("DB_PORT", default="3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
            "TEST": {
                "NAME": "test_elimu_school",
                "CHARSET": "utf8mb4",
                "COLLATION": "utf8mb4_unicode_ci",
            },
        }
    }


# Local default: SQLite (no MySQL/Wamp required). Production overrides to MySQL.
DATABASES = build_databases(default_engine="django.db.backends.sqlite3")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = env("LANGUAGE_CODE", default="fr-fr")
# Likasi = Africa/Lubumbashi (UTC+2). Kinshasa (UTC+1) décalait les heures d'1h.
TIME_ZONE = env("TIME_ZONE", default="Africa/Lubumbashi")
USE_I18N = True
USE_TZ = True

STATIC_URL = env("STATIC_URL", default="/static/")
STATIC_ROOT = Path(env("STATIC_ROOT", default=BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [
    BASE_DIR / "static" / "dist",
    BASE_DIR / "static" / "src",
]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=BASE_DIR / "media"))

FILE_UPLOAD_MAX_MEMORY_SIZE = env.int("FILE_UPLOAD_MAX_MEMORY_SIZE", default=10 * 1024 * 1024)
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int("DATA_UPLOAD_MAX_MEMORY_SIZE", default=12 * 1024 * 1024)

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@cs-elimu.local")
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": env("CACHE_LOCATION", default="elimu-school"),
        "TIMEOUT": env.int("CACHE_DEFAULT_TIMEOUT", default=300),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "accounts:login"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"

MAX_FAILED_LOGIN_ATTEMPTS = env("MAX_FAILED_LOGIN_ATTEMPTS")
ACCOUNT_LOCKOUT_MINUTES = env("ACCOUNT_LOCKOUT_MINUTES")

PLATFORM_NAME = env("PLATFORM_NAME", default="ELIMU One")
PLATFORM_TAGLINE = env("PLATFORM_TAGLINE", default="Système de gestion scolaire")
SCHOOL_NAME = env("SCHOOL_NAME", default="")
SCHOOL_SLOGAN = env("SCHOOL_SLOGAN", default="")
SCHOOL_CODE = env("SCHOOL_CODE", default="")
SCHOOL_REGIME = env("SCHOOL_REGIME", default="Privé agréé")
SCHOOL_VACATION = env("SCHOOL_VACATION", default="Avant et Après-midi")
SCHOOL_ADDRESS = env("SCHOOL_ADDRESS", default="")
SCHOOL_CITY = env("SCHOOL_CITY", default="")
SCHOOL_BP = env("SCHOOL_BP", default="")
SCHOOL_PHONE = env("SCHOOL_PHONE", default="")
SCHOOL_LOGO = BASE_DIR / "static" / "src" / "images" / "branding" / "logo.png"
APP_VERSION = env("APP_VERSION", default="1.0.0")

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://127.0.0.1:8000", "http://localhost:8000"],
)
CORS_ALLOW_CREDENTIALS = True
# Flutter Web (Edge/Chrome) tourne sur un port local dynamique.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.api.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "EXCEPTION_HANDLER": "apps.api.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Firebase Cloud Messaging HTTP v1 (API legacy désactivée sur Firebase).
FCM_PROJECT_ID = env("FCM_PROJECT_ID", default="institut-kalunga")
FCM_SERVICE_ACCOUNT_FILE = env("FCM_SERVICE_ACCOUNT_FILE", default="")
# Ancien champ legacy — ignoré si compte de service présent.
FCM_SERVER_KEY = env("FCM_SERVER_KEY", default="")

DATE_FORMAT = "j F Y"
DATETIME_FORMAT = "j F Y à H\\hi"
SHORT_DATE_FORMAT = "d/m/Y"
SHORT_DATETIME_FORMAT = "d/m/Y H:i"
