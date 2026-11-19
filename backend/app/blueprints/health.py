"""Endpoint status aplikasi: GET /health dan GET /api/health."""

from __future__ import annotations

import logging

from flask import Blueprint, current_app
from sqlalchemy import text

from ..extensions import db
from ..ml import get_registry
from ..responses import ok

logger = logging.getLogger(__name__)

bp = Blueprint("health", __name__)


def _check_database_connection() -> tuple[bool, str | None]:
    """Uji koneksi database nyata dengan SELECT 1."""
    try:
        db.session.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pemeriksaan koneksi database gagal: %s", exc)
        return False, f"{type(exc).__name__}"


@bp.get("/health")
@bp.get("/api/health")
def health():
    cfg = current_app.config
    ml_status = get_registry().status()
    db_connected, db_error = _check_database_connection()
    healthy = ml_status["model_loaded"] and ml_status["normalizer_match"] and db_connected
    return ok(
        {
            "status": "ok" if healthy else "degraded",
            "app": cfg["APP_NAME"],
            "version": cfg["APP_VERSION"],
            "environment": cfg["ENV"],
            "ml": ml_status,
            "database": {
                "configured": cfg["DATABASE_CONFIGURED"],
                "connected": db_connected,
                "mode": "session_pooler",
                "error": db_error,
            },
            "integrations": {
                "google_oauth_configured": bool(cfg["GOOGLE_CLIENT_ID"] and cfg["GOOGLE_CLIENT_SECRET"]),
                "gemini_configured": bool(cfg["GEMINI_API_KEY"]),
                "groq_configured": bool(cfg["GROQ_API_KEY"]),
            },
        }
    )
