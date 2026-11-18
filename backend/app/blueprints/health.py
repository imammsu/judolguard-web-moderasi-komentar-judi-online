"""Endpoint status aplikasi: GET /health dan GET /api/health."""

from __future__ import annotations

from flask import Blueprint, current_app

from ..ml import get_registry
from ..responses import ok

bp = Blueprint("health", __name__)


@bp.get("/health")
@bp.get("/api/health")
def health():
    cfg = current_app.config
    ml_status = get_registry().status()
    healthy = ml_status["model_loaded"] and ml_status["normalizer_match"]
    return ok(
        {
            "status": "ok" if healthy else "degraded",
            "app": cfg["APP_NAME"],
            "version": cfg["APP_VERSION"],
            "environment": cfg["ENV"],
            "ml": ml_status,
            "database": {
                # Status koneksi nyata ditambahkan pada Part 3.
                "configured": cfg["DATABASE_CONFIGURED"],
                "mode": "session_pooler",
            },
            "integrations": {
                "google_oauth_configured": bool(cfg["GOOGLE_CLIENT_ID"] and cfg["GOOGLE_CLIENT_SECRET"]),
                "gemini_configured": bool(cfg["GEMINI_API_KEY"]),
                "groq_configured": bool(cfg["GROQ_API_KEY"]),
            },
        }
    )
