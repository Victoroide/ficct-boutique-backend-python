"""Base settings shared by dev / prod environments."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "insecure-dev-secret-change-me")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    # local
    "apps.common",
    "apps.ai_catalog",
    "apps.forecasting",
    "apps.clustering",
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
ASGI_APPLICATION = "config.asgi.application"

# This service is stateless for relational data; it speaks to DynamoDB.
# A SQLite DB is configured purely so Django auth/migrations don't error;
# we don't depend on it for any business data.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # File path is /tmp so the container's non-root user can always create
        # the file. Override via SQLITE_PATH env var in deployments that need
        # persistence. Business data lives in DynamoDB, not here.
        "NAME": os.getenv("SQLITE_PATH", "/tmp/ai_service.sqlite3"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.common.auth.jwt_authentication.RS256JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FICCT Boutique AI Service",
    "DESCRIPTION": "Image similarity, demand forecasting, customer clustering.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:4200").split(",")
    if o.strip()
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"time":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","msg":"%(message)s"}',
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}

# Application-specific configuration
FICCT_AI = {
    "JWT_PUBLIC_KEY_PATH": os.getenv("JWT_PUBLIC_KEY_PATH", "/app/.tools/keys/jwt_public_dev.pem"),
    # Production injects the Go core prod public key as a PEM string (preferred
    # over the baked dev key file).
    "JWT_PUBLIC_KEY_PEM": os.getenv("JWT_PUBLIC_KEY_PEM", ""),
    "JWT_ISSUER": os.getenv("JWT_ISSUER", "ficct-go"),
    "JWT_AUDIENCE": os.getenv("JWT_AUDIENCE", "ficct-django"),
    "DYNAMODB_ENDPOINT": os.getenv("DYNAMODB_ENDPOINT", "http://dynamodb:8000"),
    "DYNAMODB_REGION": os.getenv("DYNAMODB_REGION", "us-east-1"),
    "DYNAMODB_ACCESS_KEY_ID": os.getenv("DYNAMODB_ACCESS_KEY_ID", "local"),
    "DYNAMODB_SECRET_ACCESS_KEY": os.getenv("DYNAMODB_SECRET_ACCESS_KEY", "local"),
    "DYNAMODB_TABLE_PREFIX": os.getenv("DYNAMODB_TABLE_PREFIX", "ficct_"),
    "GO_CORE_BASE_URL": os.getenv("GO_CORE_BASE_URL", "http://host.docker.internal:8080"),
    "GO_CORE_TIMEOUT_SECONDS": int(os.getenv("GO_CORE_TIMEOUT_SECONDS", "30")),
}
