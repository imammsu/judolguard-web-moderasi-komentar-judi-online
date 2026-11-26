"""Command Telegram dasar dan pairing akun JudolGuard."""

from __future__ import annotations

import asyncio
import logging
from typing import Final

from telegram import Update
from telegram.ext import ContextTypes

from ..services.telegram_pairing import PairingError, consume_pairing_token

logger = logging.getLogger(__name__)

HELP_TEXT: Final = """Perintah JudolGuard Sentinel:

/start - Mulai menggunakan bot
/bantuan - Menampilkan bantuan
/status - Melihat status patroli
/stats - Melihat statistik komentar
/topspammer - Melihat akun spam terbanyak
/pause - Menjeda patroli
/resume - Melanjutkan patroli
/putuskan - Memutuskan akun Telegram
"""

PLANNED_COMMANDS: Final[tuple[tuple[str, str], ...]] = (
    ("start", "Mulai menggunakan bot"),
    ("bantuan", "Menampilkan bantuan"),
    ("status", "Melihat status patroli"),
    ("stats", "Melihat statistik komentar"),
    ("topspammer", "Melihat akun spam terbanyak"),
    ("pause", "Menjeda patroli"),
    ("resume", "Melanjutkan patroli"),
    ("putuskan", "Memutuskan akun Telegram"),
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pairing otomatis dari deep link atau berikan petunjuk penggunaan."""
    message = update.effective_message
    if message is None:
        return

    if context.args:
        application = getattr(context, "application", None)
        flask_app = getattr(application, "bot_data", {}).get("flask_app")
        chat = getattr(update, "effective_chat", None)
        raw_token = context.args[0]
        if flask_app is None or chat is None:
            await message.reply_text(
                "Pairing belum dapat diproses karena worker belum terhubung "
                "ke aplikasi JudolGuard."
            )
            return

        def pair() -> None:
            with flask_app.app_context():
                consume_pairing_token(raw_token, int(chat.id))

        try:
            await asyncio.to_thread(pair)
        except PairingError as exc:
            await message.reply_text(exc.message)
            return
        except Exception:  # noqa: BLE001
            logger.exception("Gagal memproses pairing Telegram.")
            await message.reply_text(
                "Pairing tidak dapat diproses sekarang. Silakan buat tautan baru "
                "dari aplikasi JudolGuard."
            )
            return

        await message.reply_text(
            "Telegram berhasil terhubung ke JudolGuard.\n\n"
            "Notifikasi Sentinel akan dikirim ke chat ini setelah patroli "
            "diaktifkan."
        )
        return

    await message.reply_text(
        "Halo, ini JudolGuard Sentinel.\n\n"
        "Untuk menghubungkan akun Telegram:\n"
        "1. Buka aplikasi JudolGuard.\n"
        "2. Pilih menu Hubungkan Telegram.\n"
        "3. Ikuti tautan pairing yang diberikan.\n\n"
        "Ketik /bantuan untuk melihat daftar perintah."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tampilkan daftar command yang tersedia dan yang akan datang."""
    del context
    message = update.effective_message
    if message is not None:
        await message.reply_text(HELP_TEXT)


async def not_ready_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Jaga command terdaftar tetap informatif sebelum tahap berikutnya."""
    del context
    message = update.effective_message
    if message is not None:
        await message.reply_text(
            "Perintah ini belum tersedia. Fitur pairing dan patroli akan "
            "diaktifkan pada tahap implementasi berikutnya."
        )
