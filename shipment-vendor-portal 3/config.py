"""Configuration module.

Reads from environment variables (loaded by python-dotenv from .env).
Three environments are supported: development, testing, production.
Pick one with FLASK_ENV.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env once at import time
load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


class BaseConfig:
    """Shared defaults for all environments."""

    # --- Flask core ---
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    JSON_SORT_KEYS = False

    # --- DB ---
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(os.path.dirname(__file__), "instance", "svp.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # --- Sessions ---
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=14)

    # --- JWT ---
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)

    # --- Mail ---
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = _bool("MAIL_USE_TLS", True)
    MAIL_USE_SSL = _bool("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER", "Shipment Portal <noreply@example.com>"
    )
    MAIL_SUPPRESS_SEND = _bool("MAIL_SUPPRESS_SEND", False)
    ADMIN_NOTIFY_EMAIL = os.getenv("ADMIN_NOTIFY_EMAIL", "admin@example.com")

    # --- App ---
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "app/static/uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_MB", "20")) * 1024 * 1024
    ITEMS_PER_PAGE = int(os.getenv("ITEMS_PER_PAGE", "25"))

    # --- Business rules ---
    PAYMENT_GRACE_DAYS = int(os.getenv("PAYMENT_GRACE_DAYS", "0"))
    DELAY_THRESHOLD_DAYS = int(os.getenv("DELAY_THRESHOLD_DAYS", "0"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config():
    name = os.getenv("FLASK_ENV", "development").lower()
    return config_by_name.get(name, DevelopmentConfig)
