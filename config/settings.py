import importlib.util
import os
from pathlib import Path
from urllib.parse import unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent.parent

if importlib.util.find_spec("dotenv"):
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-demo-only-change-me-in-production")
DEBUG = os.getenv("DEBUG", "True").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [host.strip() for host in os.getenv(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,.pythonanywhere.com,.railway.app"
).split(",") if host.strip()]
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

if RAILWAY_PUBLIC_DOMAIN and RAILWAY_PUBLIC_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "menu",
    "reservations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "reservations.middleware.SiteVisitMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

WHITENOISE_AVAILABLE = importlib.util.find_spec("whitenoise") is not None
if WHITENOISE_AVAILABLE:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

database_url = os.getenv("DATABASE_URL")
# The value shown in documentation is a placeholder; keep local development on SQLite until it is replaced.
if database_url and "@host:" not in database_url:
    parsed_database_url = urlparse(database_url)
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed_database_url.path.lstrip("/")),
        "USER": unquote(parsed_database_url.username or ""),
        "PASSWORD": unquote(parsed_database_url.password or ""),
        "HOST": parsed_database_url.hostname or "",
        "PORT": parsed_database_url.port or "",
        "CONN_MAX_AGE": 600,
        "OPTIONS": {"sslmode": "require"} if os.getenv("DATABASE_SSL", "True").lower() in {"1", "true", "yes"} else {},
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uz-latn"
TIME_ZONE = os.getenv("APP_TIMEZONE", "Asia/Tashkent")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage" if WHITENOISE_AVAILABLE else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(
    os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "staff:login"
LOGIN_REDIRECT_URL = "staff:dashboard"
LOGOUT_REDIRECT_URL = "staff:login"

SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000").rstrip("/")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PRIMARY_OWNER_TELEGRAM_ID = os.getenv("PRIMARY_OWNER_TELEGRAM_ID", "")

# Railway automatically provides this variable.
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

# Automatically trust Railway public domain + explicitly configured domains.
CSRF_TRUSTED_ORIGINS = []

if SITE_URL.startswith("https://"):
    CSRF_TRUSTED_ORIGINS.append(SITE_URL)

if RAILWAY_PUBLIC_DOMAIN:
    railway_origin = f"https://{RAILWAY_PUBLIC_DOMAIN}"
    if railway_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(railway_origin)

for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(","):
    origin = origin.strip().rstrip("/")
    if origin and origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

DEBUG = os.getenv(
    "DEBUG",
    "False" if os.getenv("RAILWAY_PROJECT_ID") else "True",
).lower() in {"1", "true", "yes", "on"}