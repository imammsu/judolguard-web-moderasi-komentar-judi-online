"""Command Telegram dasar dan pairing akun JudolGuard."""

from __future__ import annotations

import asyncio
import html
import logging
from datetime import UTC, datetime
from typing import Any, Final

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ..repositories import (
    comment_repo,
    monitored_video_repo,
    patrol_repo,
    telegram_repo,
    video_repo,
)
from ..services.telegram_pairing import PairingError, consume_pairing_token

logger = logging.getLogger(__name__)

HELP_TEXT: Final = """Perintah JudolGuard Sentinel:

/start - Mulai menggunakan bot
/bantuan - Menampilkan bantuan
/status - Melihat status patroli
/stats - Melihat statistik komentar
/topspammer - Melihat akun spam terbanyak
/pantau - Memilih video untuk dipantau
/pantauan - Melihat video yang sedang dipantau
/berhentipantau - Menghentikan pemantauan video
/pause - Menjeda patroli dan notifikasi
/resume - Melanjutkan patroli dan notifikasi
/putuskan - Memutuskan akun Telegram
"""

PLANNED_COMMANDS: Final[tuple[tuple[str, str], ...]] = (
    ("start", "Mulai menggunakan bot"),
    ("bantuan", "Menampilkan bantuan"),
    ("status", "Melihat status patroli"),
    ("stats", "Melihat statistik komentar"),
    ("topspammer", "Melihat akun spam terbanyak"),
    ("pantau", "Memilih video untuk dipantau"),
    ("pantauan", "Melihat video yang dipantau"),
    ("berhentipantau", "Menghentikan pemantauan video"),
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
    """Tampilkan daftar command Sentinel."""
    del context
    message = update.effective_message
    if message is not None:
        await message.reply_text(HELP_TEXT)


def _get_flask_app(context: ContextTypes.DEFAULT_TYPE) -> Any | None:
    application = getattr(context, "application", None)
    return getattr(application, "bot_data", {}).get("flask_app")


def _get_chat_id(update: Update) -> int | None:
    chat = getattr(update, "effective_chat", None)
    return int(chat.id) if chat is not None else None


def _owner_for_chat(app: Any, chat_id: int) -> dict[str, Any] | None:
    with app.app_context():
        pair = telegram_repo.get_owner_by_chat_id(chat_id)
        if pair is None:
            return None
        user, link = pair
        return {
            "user_id": user.id,
            "channel_id": user.channel_id,
            "paused": bool(link.paused),
            "chat_id": link.chat_id,
        }


async def _require_owner(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[Any, int, dict[str, Any]] | None:
    message = update.effective_message
    chat_id = _get_chat_id(update)
    app = _get_flask_app(context)
    if message is None or chat_id is None or app is None:
        if message is not None:
            await message.reply_text(
                "Command belum dapat diproses karena worker belum terhubung "
                "ke aplikasi JudolGuard."
            )
        return None

    owner = await asyncio.to_thread(_owner_for_chat, app, chat_id)
    if owner is None:
        await message.reply_text(
            "Telegram belum terhubung ke JudolGuard. "
            "Gunakan tombol Hubungkan Telegram dari web."
        )
        return None
    return app, chat_id, owner


def _status_data(app: Any, owner: dict[str, Any]) -> dict[str, Any]:
    with app.app_context():
        video_count, last_checked = monitored_video_repo.get_user_monitor_summary(
            owner["user_id"]
        )
        latest_run = patrol_repo.get_latest_patrol_run(owner["user_id"])
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            "paused": owner["paused"],
            "video_count": video_count,
            "last_checked": last_checked,
            "judol_today": comment_repo.count_today_judol(owner["channel_id"], today),
            "latest_error": latest_run.error if latest_run else None,
            "interval": int(app.config.get("SENTINEL_POLL_INTERVAL_SECONDS", 300)),
        }


def _stats_data(app: Any, owner: dict[str, Any]) -> list[dict[str, Any]]:
    with app.app_context():
        rows = comment_repo.get_video_stats(owner["channel_id"])
        for row in rows:
            video = video_repo.get_video_by_id(row["video_id"])
            row["title"] = video.title if video and video.title else row["video_id"]
        return rows


def _top_spammer_data(app: Any, owner: dict[str, Any]) -> list[dict[str, Any]]:
    with app.app_context():
        return comment_repo.get_top_spammers(owner["channel_id"], limit=10)


def _format_time(value: datetime | None) -> str:
    if value is None:
        return "Belum ada pemeriksaan"
    return value.astimezone(UTC).strftime("%d %b %Y %H:%M UTC")


async def _reply_html(message: Any, text: str) -> None:
    max_length = 3900
    if len(text) <= max_length:
        await message.reply_text(text, parse_mode="HTML")
        return
    lines: list[str] = []
    current = ""
    for line in text.splitlines():
        if current and len(current) + len(line) + 1 > max_length:
            lines.append(current)
            current = ""
        current = f"{current}\n{line}".strip()
    if current:
        lines.append(current)
    for chunk in lines:
        await message.reply_text(chunk, parse_mode="HTML")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    required = await _require_owner(update, context)
    if required is None:
        return
    app, _chat_id, owner = required
    message = update.effective_message
    data = await asyncio.to_thread(_status_data, app, owner)
    state = "Dijeda" if data["paused"] else "Aktif"
    text = (
        "📊 <b>Status JudolGuard</b>\n\n"
        f"Patroli: <b>{state}</b>\n"
        f"Video dipantau: <b>{data['video_count']}</b>\n"
        f"Pemeriksaan terakhir: <b>{_format_time(data['last_checked'])}</b>\n"
        f"Komentar judol hari ini: <b>{data['judol_today']}</b>\n"
        f"Interval: <b>{data['interval']} detik</b>"
    )
    if data["latest_error"]:
        text += "\nStatus terakhir: <b>terdapat error</b>"
    await _reply_html(message, text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    required = await _require_owner(update, context)
    if required is None:
        return
    app, _chat_id, owner = required
    message = update.effective_message
    rows = await asyncio.to_thread(_stats_data, app, owner)
    if not rows:
        await message.reply_text("Belum ada statistik komentar.")
        return

    lines = ["📈 <b>Statistik Komentar</b>", ""]
    for index, row in enumerate(rows, start=1):
        title = html.escape(str(row["title"]))
        lines.extend(
            [
                f"<b>{index}. {title}</b>",
                f"🔴 Judol: {row['judol_count']}",
                f"🟡 Review: {row['review_count']}",
                f"🟢 Normal: {row['normal_count']}",
                "",
            ]
        )
    await _reply_html(message, "\n".join(lines).rstrip())


async def topspammer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    required = await _require_owner(update, context)
    if required is None:
        return
    app, _chat_id, owner = required
    message = update.effective_message
    rows = await asyncio.to_thread(_top_spammer_data, app, owner)
    if not rows:
        await message.reply_text("Belum ada akun spam terdeteksi.")
        return

    lines = ["🏆 <b>Top Spammer</b>", ""]
    for index, row in enumerate(rows, start=1):
        name = html.escape(str(row["author_name"]))
        lines.append(f"{index}. {name} — <b>{row['comment_count']}</b> komentar")
    await _reply_html(message, "\n".join(lines))


MONITOR_PAGE_SIZE: Final = 8
MONITOR_CALLBACK_PREFIX: Final = "monitor"


def _monitor_page(
    app: Any,
    owner: dict[str, Any],
    *,
    page: int,
    active_only: bool,
) -> tuple[str, InlineKeyboardMarkup]:
    with app.app_context():
        if active_only:
            monitored = monitored_video_repo.list_active_monitored_videos(owner["user_id"])
            all_videos = [
                video_repo.get_video(owner["channel_id"], row.video_id)
                for row in monitored
            ]
            all_videos = [video for video in all_videos if video is not None]
            total_count = len(all_videos)
            total_pages = max(1, (total_count + MONITOR_PAGE_SIZE - 1) // MONITOR_PAGE_SIZE)
            page = min(max(page, 1), total_pages)
            page_videos = all_videos[
                (page - 1) * MONITOR_PAGE_SIZE : page * MONITOR_PAGE_SIZE
            ]
        else:
            total_count = video_repo.count_videos(owner["channel_id"])
            total_pages = max(1, (total_count + MONITOR_PAGE_SIZE - 1) // MONITOR_PAGE_SIZE)
            page = min(max(page, 1), total_pages)
            page_videos = video_repo.list_videos(
                owner["channel_id"],
                page,
                MONITOR_PAGE_SIZE,
            )
        active_ids = {
            row.video_id
            for row in monitored_video_repo.list_active_monitored_videos(owner["user_id"])
        }

    if not page_videos:
        text = (
            "Belum ada video pada katalog lokal.\n"
            "Buka aplikasi web dan refresh daftar video terlebih dahulu."
        )
        return text, InlineKeyboardMarkup([])

    action = "berhenti" if active_only else "toggle"
    lines = [
        (
            "🎥 <b>Pilih video yang dipantau</b>"
            if not active_only
            else "🎥 <b>Video yang sedang dipantau</b>"
        ),
        "",
    ]
    buttons: list[list[InlineKeyboardButton]] = []
    for video in page_videos:
        title = str(video.title or video.video_id)
        label = title[:48] + "…" if len(title) > 49 else title
        if video.video_id in active_ids:
            label = f"✅ {label}"
        buttons.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=(
                        f"{MONITOR_CALLBACK_PREFIX}:"
                        f"{action}:{video.video_id}:{page}:{int(active_only)}"
                    ),
                )
            ]
        )
        lines.append(f"• {html.escape(title)}")

    navigation: list[InlineKeyboardButton] = []
    if page > 1:
        navigation.append(
            InlineKeyboardButton(
                "‹ Sebelumnya",
                callback_data=f"{MONITOR_CALLBACK_PREFIX}:page:{page - 1}:{int(active_only)}",
            )
        )
    if page < total_pages:
        navigation.append(
            InlineKeyboardButton(
                "Berikutnya ›",
                callback_data=f"{MONITOR_CALLBACK_PREFIX}:page:{page + 1}:{int(active_only)}",
            )
        )
    if navigation:
        buttons.append(navigation)
    lines.extend(["", f"Halaman {page}/{total_pages}"])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


async def _monitor_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    active_only: bool,
) -> None:
    required = await _require_owner(update, context)
    if required is None:
        return
    app, _chat_id, owner = required
    message = update.effective_message
    text, markup = await asyncio.to_thread(
        _monitor_page,
        app,
        owner,
        page=1,
        active_only=active_only,
    )
    await message.reply_text(text, parse_mode="HTML", reply_markup=markup)


async def monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _monitor_command(update, context, active_only=False)


async def monitored_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _monitor_command(update, context, active_only=True)


async def stop_monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _monitor_command(update, context, active_only=True)


def _toggle_monitoring(
    app: Any,
    chat_id: int,
    video_id: str,
    *,
    active: bool | None,
) -> tuple[bool, str]:
    with app.app_context():
        pair = telegram_repo.get_owner_by_chat_id(chat_id)
        if pair is None:
            return False, "Telegram belum terhubung ke JudolGuard."
        user, _link = pair
        video = video_repo.get_video(user.channel_id, video_id)
        if video is None:
            return False, "Video tidak ditemukan atau bukan milik channel Anda."
        current = monitored_video_repo.get_monitored_video(user.id, video_id)
        next_active = not current.active if active is None and current else bool(active)
        active_count = len(monitored_video_repo.list_active_monitored_videos(user.id))
        max_active = max(
            1,
            int(app.config.get("SENTINEL_MAX_MONITORED_VIDEOS", 50)),
        )
        if next_active and (current is None or not current.active) and active_count >= max_active:
            return False, f"Batas {max_active} video aktif telah tercapai."
        monitored_video_repo.set_monitoring(
            user.id,
            video_id,
            active=next_active,
            reset_baseline=next_active,
        )
        return True, (
            "✅ Video ditambahkan ke pemantauan. "
            "Baseline akan dibuat pada patroli berikutnya."
            if next_active
            else "⏸️ Pemantauan video dihentikan."
        )


async def monitor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    await query.answer()
    app = _get_flask_app(context)
    message = query.message
    chat = getattr(update, "effective_chat", None)
    if app is None or message is None or chat is None:
        return

    parts = query.data.split(":")
    try:
        action = parts[1]
        page = int(parts[-2])
        active_only = bool(int(parts[-1]))
    except (IndexError, ValueError):
        await query.edit_message_text("Pilihan monitoring tidak valid.")
        return

    owner = await asyncio.to_thread(_owner_for_chat, app, int(chat.id))
    if owner is None:
        await query.edit_message_text("Telegram belum terhubung ke JudolGuard.")
        return

    if action == "page":
        text, markup = await asyncio.to_thread(
            _monitor_page,
            app,
            owner,
            page=page,
            active_only=active_only,
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        return

    if action not in {"toggle", "berhenti"} or len(parts) < 5:
        await query.edit_message_text("Pilihan monitoring tidak valid.")
        return

    video_id = parts[2]
    active = False if action == "berhenti" else None
    success, result_text = await asyncio.to_thread(
        _toggle_monitoring,
        app,
        int(chat.id),
        video_id,
        active=active,
    )
    if not success:
        await query.edit_message_text(result_text)
        return

    text, markup = await asyncio.to_thread(
        _monitor_page,
        app,
        owner,
        page=page,
        active_only=active_only,
    )
    await query.edit_message_text(
        f"{result_text}\n\n{text}",
        parse_mode="HTML",
        reply_markup=markup,
    )


async def _set_pause_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    paused: bool,
) -> None:
    required = await _require_owner(update, context)
    if required is None:
        return
    app, chat_id, _owner = required
    message = update.effective_message

    def update_link() -> bool:
        with app.app_context():
            return telegram_repo.set_paused_by_chat_id(chat_id, paused)

    updated = await asyncio.to_thread(update_link)
    if not updated:
        await message.reply_text("Link Telegram tidak ditemukan.")
        return
    if paused:
        await message.reply_text(
            "Patroli dan notifikasi dijeda. Pairing Telegram tetap tersimpan."
        )
    else:
        await message.reply_text("Patroli dan notifikasi dilanjutkan.")


async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_pause_command(update, context, paused=True)


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_pause_command(update, context, paused=False)


async def disconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    required = await _require_owner(update, context)
    if required is None:
        return
    app, chat_id, _owner = required
    message = update.effective_message

    def unlink() -> bool:
        with app.app_context():
            return telegram_repo.unlink_by_chat_id(chat_id)

    removed = await asyncio.to_thread(unlink)
    if removed:
        await message.reply_text(
            "Telegram berhasil diputuskan dari JudolGuard. "
            "Lakukan pairing ulang dari web jika ingin menghubungkan kembali."
        )
    else:
        await message.reply_text("Link Telegram tidak ditemukan.")


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
