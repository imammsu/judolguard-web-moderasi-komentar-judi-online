"""Uji command Telegram Sentinel dengan ownership berbasis chat_id."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.extensions import db
from app.models import Comment, MonitoredVideo, PatrolRun, TelegramLink, Video
from app.repositories import user_repo
from app.telegram.commands import (
    disconnect_command,
    monitor_callback,
    monitor_command,
    pause_command,
    resume_command,
    stats_command,
    status_command,
    stop_monitor_command,
    topspammer_command,
)


class _FakeMessage:
    def __init__(self) -> None:
        self.responses: list[tuple[str, dict[str, object]]] = []

    async def reply_text(self, text: str, **kwargs) -> None:
        self.responses.append((text, kwargs))


class _FakeCallbackQuery:
    def __init__(self, data: str, message: _FakeMessage) -> None:
        self.data = data
        self.message = message
        self.answered = False
        self.edited: list[tuple[str, dict[str, object]]] = []

    async def answer(self) -> None:
        self.answered = True

    async def edit_message_text(self, text: str, **kwargs) -> None:
        self.edited.append((text, kwargs))


def _context(app):
    return SimpleNamespace(
        args=[],
        application=SimpleNamespace(bot_data={"flask_app": app}),
    )


def _update(chat_id: int) -> tuple[SimpleNamespace, _FakeMessage]:
    message = _FakeMessage()
    return (
        SimpleNamespace(
            effective_message=message,
            effective_chat=SimpleNamespace(id=chat_id),
        ),
        message,
    )


def _seed_command_user(app) -> int:
    with app.app_context():
        user = user_repo.upsert_user(
            channel_id="UC_COMMAND_OWNER",
            email="command@example.com",
            refresh_token_plain="refresh-token",
        )
        db.session.add(
            TelegramLink(
                user_id=user.id,
                chat_id=1001,
                paused=False,
            )
        )
        db.session.add(
            Video(
                video_id="video-command",
                owner_channel_id=user.channel_id,
                title="Video Command",
                comment_count=4,
            )
        )
        now = datetime.now(UTC)
        db.session.add(
            MonitoredVideo(
                user_id=user.id,
                video_id="video-command",
                last_comment_count=4,
                last_checked_at=now,
                active=True,
            )
        )
        db.session.add(
            PatrolRun(
                user_id=user.id,
                run_at=now,
                videos_checked=1,
                est_api_units=3,
                new_comments=3,
                alerts_sent=1,
            )
        )
        db.session.add_all(
            [
                Comment(
                    comment_id="command-judol-1",
                    video_id="video-command",
                    owner_channel_id=user.channel_id,
                    author_name="Spam A",
                    author_channel_id="UC_SPAM_A",
                    text_original="judol satu",
                    published_at=now,
                    zone="judol",
                    score=0.99,
                    model_version="test",
                    classified_at=now,
                    moderation_status="none",
                ),
                Comment(
                    comment_id="command-judol-2",
                    video_id="video-command",
                    owner_channel_id=user.channel_id,
                    author_name="Spam A",
                    author_channel_id="UC_SPAM_A",
                    text_original="judol dua",
                    published_at=now - timedelta(minutes=1),
                    zone="judol",
                    score=0.98,
                    model_version="test",
                    classified_at=now,
                    moderation_status="none",
                ),
                Comment(
                    comment_id="command-review",
                    video_id="video-command",
                    owner_channel_id=user.channel_id,
                    author_name="Reviewer",
                    author_channel_id="UC_REVIEWER",
                    text_original="perlu review",
                    published_at=now,
                    zone="review",
                    score=0.5,
                    model_version="test",
                    classified_at=now,
                    moderation_status="none",
                ),
                Comment(
                    comment_id="command-normal",
                    video_id="video-command",
                    owner_channel_id=user.channel_id,
                    author_name="Penonton",
                    author_channel_id="UC_VIEWER",
                    text_original="normal",
                    published_at=now,
                    zone="bukan",
                    score=0.01,
                    model_version="test",
                    classified_at=now,
                    moderation_status="none",
                ),
                Comment(
                    comment_id="command-rejected",
                    video_id="video-command",
                    owner_channel_id=user.channel_id,
                    author_name="Spam Rejected",
                    author_channel_id="UC_REJECTED",
                    text_original="rejected",
                    published_at=now,
                    zone="judol",
                    score=0.99,
                    model_version="test",
                    classified_at=now,
                    moderation_status="rejected",
                ),
            ]
        )
        db.session.commit()
        return user.id


def test_status_stats_and_topspammer_are_scoped_to_linked_user(app):
    _seed_command_user(app)
    context = _context(app)

    update, message = _update(1001)
    asyncio.run(status_command(update, context))
    assert "Patroli: <b>Aktif</b>" in message.responses[0][0]
    assert "Komentar judol hari ini: <b>2</b>" in message.responses[0][0]

    update, message = _update(1001)
    asyncio.run(stats_command(update, context))
    stats_text = message.responses[0][0]
    assert "Video Command" in stats_text
    assert "Judol: 2" in stats_text
    assert "Review: 1" in stats_text
    assert "Normal: 1" in stats_text

    update, message = _update(1001)
    asyncio.run(topspammer_command(update, context))
    assert "Spam A" in message.responses[0][0]
    assert "2" in message.responses[0][0]
    assert "Spam Rejected" not in message.responses[0][0]


def test_pause_resume_and_disconnect_change_telegram_link(app):
    user_id = _seed_command_user(app)
    context = _context(app)

    update, message = _update(1001)
    asyncio.run(pause_command(update, context))
    assert "dijeda" in message.responses[0][0].lower()
    with app.app_context():
        link = db.session.query(TelegramLink).filter_by(user_id=user_id).one()
        assert link.paused is True

    update, message = _update(1001)
    asyncio.run(resume_command(update, context))
    assert "dilanjutkan" in message.responses[0][0].lower()
    with app.app_context():
        link = db.session.query(TelegramLink).filter_by(user_id=user_id).one()
        assert link.paused is False

    update, message = _update(1001)
    asyncio.run(disconnect_command(update, context))
    assert "diputuskan" in message.responses[0][0].lower()
    with app.app_context():
        assert db.session.query(TelegramLink).filter_by(user_id=user_id).one_or_none() is None
        assert db.session.get(Video, "video-command") is not None
        assert db.session.get(Comment, "command-judol-1") is not None

    update, message = _update(1001)
    asyncio.run(status_command(update, context))
    assert "belum terhubung" in message.responses[0][0].lower()


def test_monitor_command_lists_videos_and_callback_toggles_selection(app):
    _seed_command_user(app)
    context = _context(app)

    update, message = _update(1001)
    asyncio.run(monitor_command(update, context))

    assert "Video Command" in message.responses[0][0]
    markup = message.responses[0][1]["reply_markup"]
    callback_data = markup.inline_keyboard[0][0].callback_data
    assert callback_data == "monitor:toggle:video-command:1:0"

    callback_message = _FakeMessage()
    callback = _FakeCallbackQuery(callback_data, callback_message)
    callback_update = SimpleNamespace(
        callback_query=callback,
        effective_chat=SimpleNamespace(id=1001),
    )
    asyncio.run(monitor_callback(callback_update, context))

    assert callback.answered is True
    assert "Pemantauan video dihentikan" in callback.edited[0][0]
    with app.app_context():
        monitored = db.session.query(MonitoredVideo).one()
        assert monitored.active is False


def test_stop_monitor_command_shows_only_active_videos(app):
    _seed_command_user(app)
    context = _context(app)

    update, message = _update(1001)
    asyncio.run(stop_monitor_command(update, context))

    assert "Video yang sedang dipantau" in message.responses[0][0]
    markup = message.responses[0][1]["reply_markup"]
    assert markup.inline_keyboard[0][0].callback_data == "monitor:berhenti:video-command:1:1"


def test_unpaired_chat_cannot_read_other_users_data(app):
    _seed_command_user(app)
    context = _context(app)
    update, message = _update(9999)

    asyncio.run(stats_command(update, context))

    assert "belum terhubung" in message.responses[0][0].lower()
