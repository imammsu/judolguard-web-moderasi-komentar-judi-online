"""Command Telegram dasar sebelum fitur pairing dan patroli diaktifkan."""

from __future__ import annotations

from typing import Final

from telegram import Update
from telegram.ext import ContextTypes

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
    """Berikan petunjuk pairing tanpa menyimpan token pada tahap ini."""
    message = update.effective_message
    if message is None:
        return

    if context.args:
        await message.reply_text(
            "Token pairing diterima, tetapi fitur pairing belum tersedia. "
            "Silakan coba lagi setelah proses pairing diaktifkan."
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
