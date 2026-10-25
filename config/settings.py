"""
KamKarao settings.

Everything that changes between your laptop and the live server is read from
environment variables (or a `.env` file next to manage.py). See `.env.example`.
"""
import os
from pathlib import Path

import dj_database_url
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Tiny .env reader so the project needs no extra package for it."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    return str(env(key, default)).lower() in {"1", "true", "yes", "on"}


def env_list(key, default=""):
    return [x.strip() for x in str(env(key, default)).split(",") if x.strip()]


# --- Core -------------------------------------------------------------------
DEBUG = env_bool("DEBUG", True)
SECRET_KEY = env("SECRET_KEY", "dev-only-insecure-key-change-me")
if not DEBUG and SECRET_KEY.startswith("dev-only"):
    raise RuntimeError("Set a real SECRET_KEY in the environment for production.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")
SITE_URL = env("SITE_URL", "http://127.0.0.1:8000").rstrip("/")
SITE_NAME = "KamKarao"

INSTALLED_APPS = [
    "unfold",  # modern admin theme, must come before django.contrib.admin
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "apps.core",
    "apps.providers",
    "apps.accounts",
    "apps.leads",
    "apps.ads",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "apps.core.middleware.AdminEnglishMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.accounts.middleware.CustomerMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "apps.core.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---------------------------------------------------------------
# SQLite on your laptop, PostgreSQL in production:
#   DATABASE_URL=postgres://user:pass@host:5432/kamkarao
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Language: Hindi first, English second ---------------------------------
LANGUAGE_CODE = "hi"
LANGUAGES = [("hi", "हिंदी"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --- Static and media -------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# ID photos never go in the public media folder.
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"

# Object storage (Cloudflare R2, AWS S3, DigitalOcean Spaces...). Leave
# S3_BUCKET empty to keep files on the server's disk.
S3_BUCKET = env("S3_BUCKET", "")
S3_PRIVATE_BUCKET = env("S3_PRIVATE_BUCKET", "")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        )
    },
}
if S3_BUCKET:
    _s3_common = {
        "access_key": env("S3_ACCESS_KEY"),
        "secret_key": env("S3_SECRET_KEY"),
        "endpoint_url": env("S3_ENDPOINT_URL") or None,
        "region_name": env("S3_REGION", "auto"),
    }
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3_common,
            "bucket_name": S3_BUCKET,
            "querystring_auth": False,
            "custom_domain": env("S3_PUBLIC_DOMAIN") or None,
            "file_overwrite": False,
        },
    }
    if S3_PRIVATE_BUCKET:
        STORAGES["private"] = {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                **_s3_common,
                "bucket_name": S3_PRIVATE_BUCKET,
                "querystring_auth": True,
                "querystring_expire": 300,
                "file_overwrite": False,
            },
        }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Sessions and security --------------------------------------------------
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # a verified phone stays logged in 30 days
SESSION_COOKIE_HTTPONLY = True
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_CONTENT_TYPE_NOSNIFF = True

# --- KamKarao business rules ------------------------------------------------
OTP_PROVIDER = env("OTP_PROVIDER", "console")  # none | console | msg91
OTP_LENGTH = 4
OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_SECONDS = 30
MSG91_AUTH_KEY = env("MSG91_AUTH_KEY", "")
MSG91_TEMPLATE_ID = env("MSG91_TEMPLATE_ID", "")

DAILY_REVEAL_LIMIT = int(env("DAILY_REVEAL_LIMIT", 20))
NEARBY_ONLY_KM = float(env("NEARBY_ONLY_KM", 2.5))
NEW_PROVIDER_MIN_RATINGS = 3
AUTO_PAUSE_MISSED_LEADS = 3
SUPPORT_WHATSAPP = env("SUPPORT_WHATSAPP", "")  # e.g. 919876543210
MAX_BANNERS_PER_PAGE = 2

# --- Admin panel look (django-unfold) ------------------------------------------
from django.templatetags.static import static  # noqa: E402

from apps.core.admin_nav import UNFOLD_SIDEBAR  # noqa: E402

UNFOLD = {
    "SITE_TITLE": "KamKarao admin",
    "SITE_HEADER": "KamKarao",
    "SITE_SUBHEADER": "Banda · admin panel",
    "SITE_SYMBOL": "handyman",
    "SITE_URL": "/",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
    "BORDER_RADIUS": "10px",
    "LOGIN": {"redirect_after": "/admin/"},
    "DASHBOARD_CALLBACK": "apps.core.admin_views.dashboard_callback",
    "ENVIRONMENT": "apps.core.admin_nav.environment_badge",
    "STYLES": [lambda request: static("kk-admin.css")],
    "COLORS": {
        # Same teal as the website
        "primary": {
            "50": "oklch(98.4% .014 180.72)",
            "100": "oklch(95.3% .051 180.801)",
            "200": "oklch(91% .096 180.426)",
            "300": "oklch(85.5% .138 181.071)",
            "400": "oklch(77.7% .152 181.912)",
            "500": "oklch(70.4% .14 182.503)",
            "600": "oklch(60% .118 184.704)",
            "700": "oklch(51.1% .096 186.391)",
            "800": "oklch(43.7% .078 188.216)",
            "900": "oklch(38.6% .063 188.416)",
            "950": "oklch(27.7% .046 192.524)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": UNFOLD_SIDEBAR,
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "kamkarao": {"handlers": ["console"], "level": "INFO"},
    },
}
