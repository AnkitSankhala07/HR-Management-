"""Base settings for Dayflow HRMS (shared by all environments)."""
import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

REPO_ROOT = BASE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FRONTEND_DIR = REPO_ROOT / "frontend"
load_dotenv(REPO_ROOT / ".env")


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    return env(key, str(default)).lower() in ("1", "true", "yes", "on")


SECRET_KEY = env("SECRET_KEY", "dev-insecure-change-me")
DEBUG = env_bool("DEBUG", False)

raw_hosts = env("ALLOWED_HOSTS", "localhost,127.0.0.1,.vercel.app,.onrender.com")
_hosts = []
for h in raw_hosts.split(","):
    h = h.strip()
    if not h or h.upper() == "ALLOWED_HOSTS":
        continue
    h = h.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    if h and h not in _hosts:
        _hosts.append(h)
for fallback_host in ("localhost", "127.0.0.1", ".vercel.app", ".onrender.com"):
    if fallback_host not in _hosts:
        _hosts.append(fallback_host)
ALLOWED_HOSTS = _hosts

raw_csrf = env("CSRF_TRUSTED_ORIGINS", "https://*.vercel.app,https://*.onrender.com,http://localhost:8000,http://127.0.0.1:8000")
_origins = []
for o in raw_csrf.split(","):
    o = o.strip()
    if not o or o.upper() == "CSRF_TRUSTED_ORIGINS":
        continue
    if not (o.startswith("http://") or o.startswith("https://")):
        if "." in o:
            o = f"https://{o}"
        else:
            continue
    if o and o not in _origins:
        _origins.append(o)
for fallback_origin in ("https://*.vercel.app", "https://*.onrender.com", "http://localhost:8000", "http://127.0.0.1:8000"):
    if fallback_origin not in _origins:
        _origins.append(fallback_origin)
CSRF_TRUSTED_ORIGINS = _origins

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    "apps.common",
    "apps.accounts",
    "apps.employees",
    "apps.attendance",
    "apps.leave",
    "apps.payroll",
    "apps.documents",
    "apps.notifications",
    "apps.announcements",
    "apps.goals",
    "apps.skills",
    "apps.recognition",
    "apps.recruitment",
    "apps.onboarding",
    "apps.audit",
    "apps.copilot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [
        FRONTEND_DIR / "templates",
        BASE_DIR / "templates",
    ],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "apps.common.context_processors.layout",
    ]},
}]

IS_VERCEL = bool(os.getenv("VERCEL"))

# ---- Database: MySQL 8+ (or SQLite if configured / fallback) ----
if env("DATABASE_ENGINE", "").lower() in ("sqlite", "sqlite3") or env_bool("USE_SQLITE", True) or not env("DATABASE_HOST"):
    if IS_VERCEL:
        import shutil
        import tempfile
        tmp_db = Path(tempfile.gettempdir()) / "db.sqlite3"
        bundled_db = BASE_DIR / "db.sqlite3"
        if not bundled_db.exists():
            bundled_db = REPO_ROOT / "db.sqlite3"
        if bundled_db.exists() and (not tmp_db.exists() or tmp_db.stat().st_size == 0):
            try:
                shutil.copy2(bundled_db, tmp_db)
            except Exception:
                pass
        sqlite_name = tmp_db
    else:
        sqlite_name = BASE_DIR / "db.sqlite3"
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": sqlite_name,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("DATABASE_NAME", "dayflow_hrms"),
            "USER": env("DATABASE_USER", "dayflow"),
            "PASSWORD": env("DATABASE_PASSWORD", ""),
            "HOST": env("DATABASE_HOST", "127.0.0.1"),
            "PORT": env("DATABASE_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4"},
            "CONN_MAX_AGE": 60,
            "ATOMIC_REQUESTS": False,
        }
    }
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.ComplexityValidator"},
]
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [FRONTEND_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

# ---- Sessions / cookies ----
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 8
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---- Cache (used by throttling) ----
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# ---- DRF ----
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.common.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "login": env("THROTTLE_LOGIN", "10/min"),
        "register": env("THROTTLE_REGISTER", "10/hour"),
        "password": env("THROTTLE_PASSWORD", "10/hour"),
        "public_apply": env("THROTTLE_APPLY", "20/hour"),
    },
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Dayflow HRMS API",
    "DESCRIPTION": "Every workday, perfectly aligned. Core HRMS REST API (Django REST Framework).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---- Email (optional SMTP; console backend when unset so dev never crashes) ----
EMAIL_HOST = env("EMAIL_HOST")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(env("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = env("EMAIL_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_PASSWORD")
    EMAIL_USE_TLS = True
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Dayflow HRMS <no-reply@dayflow.local>")
SITE_URL = env("SITE_URL", "http://localhost:8000")

# ---- Dayflow settings ----
REQUIRE_EMAIL_VERIFICATION = env_bool("REQUIRE_EMAIL_VERIFICATION", True)
MAX_FAILED_LOGINS = int(env("MAX_FAILED_LOGINS", "5"))
LOCKOUT_MINUTES = int(env("LOCKOUT_MINUTES", "15"))
VERIFY_TOKEN_HOURS = 24
RESET_TOKEN_HOURS = 1
WORK_DAY_HOURS = 8
FASTAPI_URL = env("FASTAPI_URL", "http://localhost:8001")           # server-to-server
FASTAPI_PUBLIC_URL = env("FASTAPI_PUBLIC_URL", "http://localhost:8001")  # browser-facing
SERVICE_JWT_SECRET = env("SERVICE_JWT_SECRET", SECRET_KEY)
SERVICE_JWT_TTL = timedelta(minutes=15)
CORS_ALLOWED_ORIGINS = [o for o in env("CORS_ALLOWED_ORIGINS", "http://localhost:8000").split(",") if o]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
    r"^https://.*\.onrender\.com$",
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
]
CORS_ALLOW_CREDENTIALS = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"std": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "std"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {"django.request": {"level": "ERROR"}},
}
AUTO_HIRE_ON_ACCEPT = env_bool("AUTO_HIRE_ON_ACCEPT", True)   # accepted offer => employee + onboarding created automatically
