"""Uji fondasi skema JudolGuard Sentinel."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Comment,
    MonitoredVideo,
    PairingToken,
    PatrolRun,
    TelegramLink,
    User,
    Video,
)


def test_sentinel_tables_are_registered(app):
    with app.app_context():
        expected = {
            "telegram_links",
            "pairing_tokens",
            "monitored_videos",
            "patrol_runs",
        }
        assert expected.issubset(set(db.metadata.tables.keys()))


def test_sentinel_defaults_and_comment_notification_state(app):
    with app.app_context():
        user = User(channel_id="UC_SENTINEL_OWNER", email="sentinel@example.com")
        db.session.add(user)
        db.session.flush()

        video = Video(
            video_id="sentinel-video",
            owner_channel_id=user.channel_id,
            title="Video Sentinel",
        )
        comment = Comment(
            comment_id="sentinel-comment",
            video_id=video.video_id,
            owner_channel_id=user.channel_id,
            text_original="Komentar uji",
        )
        link = TelegramLink(user_id=user.id, chat_id=987654321)
        token = PairingToken(
            token_hash="a" * 64,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        monitored = MonitoredVideo(
            user_id=user.id,
            video_id=video.video_id,
        )
        run = PatrolRun(user_id=user.id)
        db.session.add_all([video, comment, link, token, monitored, run])
        db.session.commit()

        assert comment.notified is False
        assert comment.notified_at is None
        assert link.paused is False
        assert link.min_alert_count == 1
        assert monitored.last_comment_count is None
        assert monitored.active is True
        assert run.videos_checked == 0
        assert run.est_api_units == 0


def test_telegram_link_and_monitored_video_are_unique_per_user(app):
    with app.app_context():
        user = User(channel_id="UC_SENTINEL_UNIQUE")
        db.session.add(user)
        db.session.flush()
        video = Video(
            video_id="sentinel-unique-video",
            owner_channel_id=user.channel_id,
            title="Video Unique",
        )
        db.session.add(video)
        db.session.flush()

        db.session.add(TelegramLink(user_id=user.id, chat_id=111))
        db.session.commit()

        db.session.add(TelegramLink(user_id=user.id, chat_id=222))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        db.session.add(
            MonitoredVideo(user_id=user.id, video_id=video.video_id)
        )
        db.session.commit()
        db.session.add(
            MonitoredVideo(user_id=user.id, video_id=video.video_id)
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
