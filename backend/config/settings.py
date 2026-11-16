"""
Django settings for the lease-abstraction-tool backend.

USE_SQLITE toggle
-----------------
When USE_SQLITE=True (the default in dev/test/CI), the backend runs entirely
against a local SQLite database and every Azure-backed integration in
apps/common/ runs in deterministic-stub mode: no network calls, no cost, no
real Azure resources required. `manage.py test` and CI always run this way.

When USE_SQLITE=False, the backend connects to real PostgreSQL using the
POSTGRES_* settings below. Each Azure integration independently switches to
its real SDK call only when that integration's own env vars are populated;
leaving an AZURE_* var blank keeps that one service stubbed even with
USE_SQLITE=False. Postgres itself is used purely as plain relational storage
-- no pgvector extension and no vector columns are used anywhere. All
vector/embedding storage goes through the Azure AI Search abstraction in
apps/common/search_store.py (with an in-memory fallback when unconfigured).
"""

from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-only-secret-key-change-me")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

USE_SQLITE = config("USE_SQLITE", default=True, cast=bool)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "apps.common",
    "apps.users",
    "apps.leases",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("POSTGRES_DB", default="lease_abstraction_tool"),
            "USER": config("POSTGRES_USER", default="lease_abstraction_tool"),
            "PASSWORD": config("POSTGRES_PASSWORD", default="lease_abstraction_tool"),
            "HOST": config("POSTGRES_HOST", default="localhost"),
            "PORT": config("POSTGRES_PORT", default="5432"),
        }
    }

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=True, cast=bool)

# --- Azure Blob Storage (apps.common.blob_store) ---
AZURE_STORAGE_CONNECTION_STRING = config("AZURE_STORAGE_CONNECTION_STRING", default="")
AZURE_STORAGE_CONTAINER = config("AZURE_STORAGE_CONTAINER", default="lease-documents")

# --- Azure AI Document Intelligence (apps.common.document_intelligence) ---
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = config("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", default="")
AZURE_DOCUMENT_INTELLIGENCE_KEY = config("AZURE_DOCUMENT_INTELLIGENCE_KEY", default="")

# --- Azure OpenAI (apps.common.ai) ---
AZURE_OPENAI_ENDPOINT = config("AZURE_OPENAI_ENDPOINT", default="")
AZURE_OPENAI_API_KEY = config("AZURE_OPENAI_API_KEY", default="")
AZURE_OPENAI_API_VERSION = config("AZURE_OPENAI_API_VERSION", default="2024-10-21")
OPENAI_CHAT_MODEL = config("OPENAI_CHAT_MODEL", default="gpt-5.4-mini")
OPENAI_EMBEDDING_MODEL = config("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-large")
EMBEDDING_DIMENSIONS = config("EMBEDDING_DIMENSIONS", default=1536, cast=int)

# --- Azure AI Search (apps.common.search_store) ---
AZURE_SEARCH_ENDPOINT = config("AZURE_SEARCH_ENDPOINT", default="")
AZURE_SEARCH_KEY = config("AZURE_SEARCH_KEY", default="")
AZURE_SEARCH_INDEX_LEASE_CHUNKS = config("AZURE_SEARCH_INDEX_LEASE_CHUNKS", default="lease_chunks")
