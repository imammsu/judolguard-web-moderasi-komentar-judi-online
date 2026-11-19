"""Konfigurasi aplikasi dari environment variable (.env di root repositori)."""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path
from urllib.parse import quote, unquote

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

load_dotenv(REPO_ROOT / ".env")

logger = logging.getLogger(__name__)


def _env(name: str, default: str = "") -> str:
    """Ambil env var; nilai kosong ("") dianggap tidak diisi."""
    value = os.getenv(name, "").strip()
    return value or default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _normalize_db_url(url: str) -> str:
    """Pakai driver psycopg v3 dan auto-encode karakter '@' di password URI Supabase."""
    if not url:
        return ""
    for prefix in ("postgres://", "postgresql://", "postgresql+psycopg://"):
        if url.startswith(prefix):
            rest = url[len(prefix) :]
            if "@" in rest:
                userinfo, _, hostpart = rest.rpartition("@")
                if ":" in userinfo:
                    user, _, raw_pass = userinfo.partition(":")
                    encoded_pass = quote(unquote(raw_pass), safe="")
                    rest = f"{user}:{encoded_pass}@{hostpart}"
            return "postgresql+psycopg://" + rest
    return url


class Config:
    APP_NAME = "JudolGuard API"
    APP_VERSION = "0.3.0"

    ENV = _env("FLASK_ENV", "production")
    DEBUG = _env("FLASK_DEBUG", "0") == "1"
    PORT = _env_int("FLASK_PORT", 5000)

    SECRET_KEY = _env("SECRET_KEY")
    FERNET_KEY = _env("FERNET_KEY")

    # Sesi: cookie HttpOnly + SameSite=Lax (satu origin, PRD 8.7 & 14.1).
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = ENV == "production"

    # Google OAuth & YouTube (Part 2 & 4)
    GOOGLE_CLIENT_ID = _env("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = _env("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = _env("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/callback")
    MAX_COMMENTS_PER_SCAN = _env_int("MAX_COMMENTS_PER_SCAN", 2000)

    # Database Supabase - Session Mode Pooler (Part 3, PRD 11.3)
    DATABASE_URL = _normalize_db_url(_env("DATABASE_URL"))
    DATABASE_CONFIGURED = bool(DATABASE_URL)
    DATA_RETENTION_DAYS = _env_int("DATA_RETENTION_DAYS", 30)
    # Selama DATABASE_URL kosong, pakai SQLite in-memory agar aplikasi tetap bisa menyala.
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = (
        {
            "pool_size": 4,
            "max_overflow": 2,
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }
        if DATABASE_CONFIGURED
        else {}
    )

    # LLM (Part 7 & 8, PRD 10.3)
    LLM_PROVIDER_ORDER = [
        p.strip() for p in _env("LLM_PROVIDER_ORDER", "gemini,groq").split(",") if p.strip()
    ]
    GEMINI_API_KEY = _env("GEMINI_API_KEY")
    GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-4-hydrogen")
    GEMINI_FALLBACK_MODEL = _env("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
    GROQ_API_KEY = _env("GROQ_API_KEY")
    GROQ_MODEL = _env("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Rate limit (Flask-Limiter). Memori proses cukup untuk satu instance.
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_HEADERS_ENABLED = True

    JSON_SORT_KEYS = False


class TestingConfig(Config):
    TESTING = True
    ENV = "testing"
    SECRET_KEY = "test-secret-key"
    FERNET_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
    GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET = "GOCSPX-test-client-secret"
    DATABASE_CONFIGURED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False


def finalize_config(config: dict) -> None:
    """Lengkapi nilai wajib yang masih kosong."""
    if not config.get("SECRET_KEY"):
        if config.get("ENV") == "production":
            raise RuntimeError("SECRET_KEY wajib diisi di .env untuk produksi")
        config["SECRET_KEY"] = secrets.token_hex(32)
        logger.warning(
            "SECRET_KEY kosong: memakai kunci acak sementara (sesi hilang saat restart). "
            "Isi SECRET_KEY di .env."
        )
