"""Factory dan lifecycle bot Telegram Sentinel."""

from __future__ import annotations

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


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catat error Telegram tanpa menulis token atau data rahasia."""
    logger.error(
        "Telegram handler error; update_type=%s error=%s",
        type(update).__name__,
        context.error,
        exc_info=context.error,
    )


def build_application(token: str) -> Application:
    """Buat aplikasi Telegram tanpa memanggil API network."""
    cleaned_token = _validate_token(token)
    application = (
        ApplicationBuilder()
        .token(cleaned_token)
        .post_init(_post_init)
        .build()
    )
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("bantuan", help_command))
    for command, _description in PLANNED_COMMANDS:
        if command not in {"start", "bantuan"}:
            application.add_handler(CommandHandler(command, not_ready_command))
    application.add_error_handler(_error_handler)
    return application


def run_bot(config: Mapping[str, Any]) -> None:
    """Jalankan long polling sampai menerima sinyal shutdown."""
    if not config.get("SENTINEL_ENABLED", False):
        raise RuntimeError(
            "SENTINEL_ENABLED=false. Ubah menjadi true pada environment worker "
            "untuk menjalankan bot Telegram."
        )

    application = build_application(str(config.get("TELEGRAM_BOT_TOKEN") or ""))
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
