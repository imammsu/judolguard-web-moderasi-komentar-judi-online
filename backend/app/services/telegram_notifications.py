"""Pembuatan dan pengiriman ringkasan alert Sentinel ke Telegram."""

from __future__ import annotations

import html
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden

from ..extensions import db
from ..models import Comment, TelegramLink, Video
from ..repositories import comment_repo, patrol_repo, telegram_repo

logger = logging.getLogger(__name__)

MAX_EXAMPLES_PER_VIDEO = 3
DEFAULT_PREVIEW_CHARS = 180


@dataclass(frozen=True)
class NotificationPlan:
    patrol_run_id: int
    user_id: int
    chat_id: int
    owner_channel_id: str
    video_id: str
    video_title: str
    comment_ids: tuple[str, ...]
    judol_count: int
    review_count: int
    examples: tuple[str, ...]
    review_url: str

    @property
    def message_html(self) -> str:
        lines = [
            "🚨 <b>Temuan komentar baru</b>",
            "",
            f"<b>Video:</b> {html.escape(self.video_title)}",
            f"🔴 Judol: <b>{self.judol_count}</b>",
            f"🟡 Perlu review: <b>{self.review_count}</b>",
        ]
        if self.examples:
            lines.extend(["", "<b>Contoh komentar:</b>"])
            lines.extend(f"• {html.escape(example)}" for example in self.examples)
        return "\n".join(lines)

    @property
    def reply_markup(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("Tinjau di web", url=self.review_url)]]
        )


@dataclass(frozen=True)
class NotificationDispatchResult:
    sent: int
    failed: int
    errors: tuple[str, ...]


class TelegramRateLimiter:
    """Rate limiter sederhana per chat untuk satu proses worker."""

    def __init__(self, max_messages_per_minute: int) -> None:
        self.limit = max(1, int(max_messages_per_minute))
        self._sent_at: dict[int, deque[datetime]] = defaultdict(deque)

    def allow(self, chat_id: int, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        cutoff = current.timestamp() - 60
        sent = self._sent_at[chat_id]
        while sent and sent[0].timestamp() <= cutoff:
            sent.popleft()
        if len(sent) >= self.limit:
            return False
        sent.append(current)
        return True


def _preview(text: str, max_chars: int) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_chars:
        return clean
    return f"{clean[: max(1, max_chars - 1)].rstrip()}…"


def build_notification_plans(
    *,
    user_id: int,
    owner_channel_id: str,
    patrol_run_id: int,
    video_ids: list[str],
    web_base_url: str,
    default_min_alert_count: int,
    max_examples: int = MAX_EXAMPLES_PER_VIDEO,
    preview_chars: int = DEFAULT_PREVIEW_CHARS,
) -> list[NotificationPlan]:
    """Buat satu plan per video dari komentar alert yang belum dinotifikasi."""
    if not video_ids:
        return []

    link = db.session.scalar(
        select(TelegramLink).where(
            TelegramLink.user_id == user_id,
            TelegramLink.paused.is_(False),
        )
    )
    if link is None:
        return []

    threshold = max(
        0,
        int(
            link.min_alert_count
            if link.min_alert_count is not None
            else default_min_alert_count
        ),
    )
    clean_ids = list(dict.fromkeys(video_id for video_id in video_ids if video_id))
    if not clean_ids:
        return []

    rows = db.session.execute(
        select(Comment, Video.title)
        .join(Video, Video.video_id == Comment.video_id)
        .where(
            Comment.owner_channel_id == owner_channel_id,
            Video.owner_channel_id == owner_channel_id,
            Comment.video_id.in_(clean_ids),
            Comment.zone.in_(("judol", "review")),
            Comment.notified.is_(False),
            Comment.moderation_status != "rejected",
        )
        .order_by(Comment.video_id.asc(), Comment.published_at.desc(), Comment.comment_id.desc())
    ).all()

    grouped: dict[str, list[tuple[Comment, str | None]]] = defaultdict(list)
    titles: dict[str, str] = {}
    for comment, title in rows:
        grouped[comment.video_id].append((comment, title))
        titles[comment.video_id] = str(title or "Video tanpa judul")

    plans: list[NotificationPlan] = []
    for video_id in clean_ids:
        comments = grouped.get(video_id, [])
        if not comments:
            continue
        judol_count = sum(comment.zone == "judol" for comment, _ in comments)
        review_count = sum(comment.zone == "review" for comment, _ in comments)
        if judol_count < threshold and review_count == 0:
            continue

        plans.append(
            NotificationPlan(
                patrol_run_id=patrol_run_id,
                user_id=user_id,
                chat_id=link.chat_id,
                owner_channel_id=owner_channel_id,
                video_id=video_id,
                video_title=titles[video_id],
                comment_ids=tuple(comment.comment_id for comment, _ in comments),
                judol_count=judol_count,
                review_count=review_count,
                examples=tuple(
                    _preview(comment.text_original, preview_chars)
                    for comment, _ in comments[: max(0, max_examples)]
                ),
                review_url=f"{web_base_url.rstrip('/')}/videos/{quote(video_id, safe='')}",
            )
        )
    return plans


async def dispatch_notifications(
    *,
    app: Any,
    bot: Any,
    plans: list[NotificationPlan],
    rate_limiter: TelegramRateLimiter,
) -> NotificationDispatchResult:
    """Kirim plan dan tandai komentar hanya setelah Telegram sukses."""
    sent = 0
    failed = 0
    errors: list[str] = []
    sent_by_run: dict[int, int] = defaultdict(int)
    errors_by_run: dict[int, list[str]] = defaultdict(list)

    for plan in plans:
        if not rate_limiter.allow(plan.chat_id):
            failed += 1
            errors.append(f"run_id={plan.patrol_run_id}: rate_limit")
            errors_by_run[plan.patrol_run_id].append("Telegram rate limit tercapai.")
            continue

        try:
            await bot.send_message(
                chat_id=plan.chat_id,
                text=plan.message_html,
                parse_mode="HTML",
                reply_markup=plan.reply_markup,
                disable_web_page_preview=True,
            )
        except Forbidden:
            failed += 1
            errors.append(f"run_id={plan.patrol_run_id}: telegram_forbidden")
            errors_by_run[plan.patrol_run_id].append(
                "Bot Telegram tidak dapat mengirim pesan ke chat ini."
            )
            with app.app_context():
                telegram_repo.pause_link(plan.user_id)
            logger.warning(
                "Telegram user diblokir atau chat tidak tersedia; user_id=%s",
                plan.user_id,
            )
            continue
        except Exception as error:  # noqa: BLE001
            failed += 1
            errors.append(f"run_id={plan.patrol_run_id}: telegram_send_failed")
            errors_by_run[plan.patrol_run_id].append(
                f"Pengiriman Telegram gagal ({type(error).__name__})."
            )
            logger.exception(
                "Pengiriman notifikasi gagal; user_id=%s video_id=%s",
                plan.user_id,
                plan.video_id,
            )
            continue

        try:
            with app.app_context():
                comment_repo.mark_comments_notified(
                    plan.owner_channel_id,
                    list(plan.comment_ids),
                )
        except Exception as error:  # noqa: BLE001
            failed += 1
            errors.append(f"run_id={plan.patrol_run_id}: notification_persist_failed")
            errors_by_run[plan.patrol_run_id].append(
                f"Status notifikasi gagal disimpan ({type(error).__name__})."
            )
            logger.exception(
                "Status notifikasi gagal disimpan; user_id=%s video_id=%s",
                plan.user_id,
                plan.video_id,
            )
            continue

        sent += 1
        sent_by_run[plan.patrol_run_id] += 1

    if sent_by_run or errors_by_run:
        with app.app_context():
            for run_id in set(sent_by_run) | set(errors_by_run):
                patrol_repo.record_notification_delivery(
                    run_id,
                    alerts_sent=sent_by_run.get(run_id, 0),
                    error="; ".join(errors_by_run.get(run_id, [])) or None,
                )

    return NotificationDispatchResult(sent, failed, tuple(errors))
