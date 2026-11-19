"""Application factory JudolGuard."""

from __future__ import annotations

import logging

from flask import Flask, abort, send_from_directory

from . import models  # noqa: F401 - daftarkan seluruh model ke SQLAlchemy metadata
from .blueprints import register_blueprints
from .config import FRONTEND_DIST, Config, finalize_config
from .errors import register_error_handlers
from .extensions import db, limiter, migrate, oauth
from .ml import get_registry
from .responses import ok
from .services.crypto import configure_fernet
from .services.oauth_service import init_oauth

_API_PREFIXES = ("api/", "auth/", "health")


def _configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
    )


def create_app(config_object: type[Config] = Config) -> Flask:
    # static_folder=None: berkas statis React disajikan oleh route penampung di bawah.
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_object)
    finalize_config(app.config)
    configure_fernet(app.config.get("FERNET_KEY"))
    _configure_logging(app.config.get("DEBUG", False))

    # Ekstensi
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    oauth.init_app(app)
    init_oauth(app)

    # Model ML dimuat SEKALI per proses (PRD 8.7)
    get_registry().load()

    register_error_handlers(app)
    register_blueprints(app)
    _register_frontend(app)
    return app


def _register_frontend(app: Flask) -> None:
    """Sajikan hasil build React (frontend/dist) dari origin yang sama (PRD 8.7)."""

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def serve_frontend(path: str):
        # Jangan menelan route API yang tidak ada: kembalikan JSON 404.
        if path.startswith(_API_PREFIXES):
            abort(404)
        index = FRONTEND_DIST / "index.html"
        if not index.exists():
            return ok(
                {
                    "message": "Frontend belum di-build. Saat pengembangan buka http://localhost:5173 "
                    "(server Vite), atau jalankan 'npm run build' di folder frontend.",
                }
            )
        target = FRONTEND_DIST / path
        if path and target.is_file():
            return send_from_directory(FRONTEND_DIST, path)
        # Route penampung agar React Router tetap berfungsi saat halaman dimuat ulang.
        return send_from_directory(FRONTEND_DIST, "index.html")
