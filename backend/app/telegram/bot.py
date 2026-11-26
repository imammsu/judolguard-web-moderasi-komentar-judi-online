"""Factory dan lifecycle bot Telegram Sentinel."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from ..sentinel.scheduler import PatrolScheduler
from .commands import (
    PLANNED_COMMANDS,
    help_command,
    not_ready_command,
    start_command,
)

logger = logging.getLogger(__name__)


def _validate_token(token: str) -> str:
    cleaned = token.strip()
    if not cleaned:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN belum diisi. Buat bot melalui @BotFather "
            "lalu isi token pada environment worker."
        )
    return cleaned


async def _post_init(application: Application) -> None:
    """Daftarkan command agar muncul pada menu Telegram."""
    await application.bot.set_my_commands(
        [BotCommand(command, description) for command, description in PLANNED_COMMANDS]
    )
    logger.info("Daftar command Telegram berhasil didaftarkan.")
    flask_app = application.bot_data.get("flask_app")
    if flask_app is not None and flask_app.config.get("SENTINEL_ENABLED", False):
        scheduler = PatrolScheduler(
            flask_app,
            int(flask_app.config.get("SENTINEL_POLL_INTERVAL_SECONDS", 300)),
            bot=application.bot,
            event_loop=asyncio.get_running_loop(),
        )
        application.bot_data["patrol_scheduler"] = scheduler
        scheduler.start()


async def _post_shutdown(application: Application) -> None:
    """Hentikan scheduler sebelum proses worker selesai."""
    scheduler = application.bot_data.get("patrol_scheduler")
    if scheduler is not None:
        await asyncio.to_thread(scheduler.stop)


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catat error Telegram tanpa menulis token atau data rahasia."""
    logger.error(
        "Telegram handler error; update_type=%s error=%s",
        type(update).__name__,
        context.error,
        exc_info=context.error,
    )


def build_application(token: str, flask_app: Any | None = None) -> Application:
    """Buat aplikasi Telegram tanpa memanggil API network."""
    cleaned_token = _validate_token(token)
    application = (
        ApplicationBuilder()
        .token(cleaned_token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    if flask_app is not None:
        application.bot_data["flask_app"] = flask_app
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("bantuan", help_command))
    for command, _description in PLANNED_COMMANDS:
        if command not in {"start", "bantuan"}:
            application.add_handler(CommandHandler(command, not_ready_command))
    application.add_error_handler(_error_handler)
    return application


def run_bot(config: Mapping[str, Any], flask_app: Any | None = None) -> None:
    """Jalankan long polling sampai menerima sinyal shutdown."""
    if not config.get("SENTINEL_ENABLED", False):
        raise RuntimeError(
            "SENTINEL_ENABLED=false. Ubah menjadi true pada environment worker "
            "untuk menjalankan bot Telegram."
        )

    application = build_application(
        str(config.get("TELEGRAM_BOT_TOKEN") or ""),
        flask_app=flask_app,
    )
    logger.info(
        "Memulai JudolGuard Sentinel Telegram dengan polling timeout=%s detik.",
        config.get("TELEGRAM_POLLING_TIMEOUT", 30),
    )
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        poll_interval=1.0,
        timeout=max(1, int(config.get("TELEGRAM_POLLING_TIMEOUT", 30))),
        drop_pending_updates=True,
    )
