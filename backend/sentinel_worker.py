"""Entrypoint proses worker Telegram JudolGuard Sentinel."""

from __future__ import annotations

import logging

from app import create_app
from app.telegram.bot import run_bot


def main() -> None:
    """Muat konfigurasi Flask lalu jalankan bot sebagai proses terpisah."""
    app = create_app()
    run_bot(app.config, flask_app=app)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
    )
    main()
