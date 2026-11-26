"""Uji pengelompokan dan pengiriman notifikasi Sentinel."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from telegram.error import Forbidden

from app.extensions import db
from app.models import Comment, PatrolRun, TelegramLink, Video
from app.repositories import patrol_repo, user_repo
from app.services.telegram_notifications import (
    TelegramRateLimiter,
    build_notification_plans,
    dispatch_notifications,
)


class _FakeBot:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.messages: list[dict[str, object]] = []

    async def send_message(self, **kwargs):
        if self.fail:
            raise RuntimeError("telegram unavailable")
        self.messages.append(kwargs)


class _ForbiddenBot:
    async def send_message(self, **kwargs):
        raise Forbidden("chat unavailable")


def _seed_alert_data(app, *, min_alert_count: int = 1) -> tuple[int, int]:
    with app.app_context():
        user = user_repo.upsert_user(
            channel_id="UC_NOTIFICATION_OWNER",
            email="notification@example.com",
            refresh_token_plain="refresh-token",
        )
        db.session.add(
            TelegramLink(
                user_id=user.id,
                chat_id=123456789,
                paused=False,
                min_alert_count=min_alert_count,
            )
        )
        db.session.add(
            Video(
                video_id="video-notification",
                owner_channel_id=user.channel_id,
                title="<Video & Judol>",
                comment_count=2,
            )
        )
        db.session.add_all(
            [
                Comment(
                    comment_id="alert-judol",
                    video_id="video-notification",
                    owner_channel_id=user.channel_id,
                    text_original="<b>info link gacor</b>",
                    zone="judol",
                    score=0.99,
                    model_version="test-model",
                    classified_at=datetime.now(UTC),
                    moderation_status="none",
                    notified=False,
                ),
                Comment(
                    comment_id="alert-review",
                    video_id="video-notification",
                    owner_channel_id=user.channel_id,
                    text_original="komentar review",
                    zone="review",
                    score=0.5,
                    model_version="test-model",
                    classified_at=datetime.now(UTC) - timedelta(seconds=1),
                    moderation_status="none",
                    notified=False,
                ),
                Comment(
                    comment_id="normal-comment",
                    video_id="video-notification",
                    owner_channel_id=user.channel_id,
                    text_original="komentar normal",
                    zone="bukan",
                    score=0.01,
                    model_version="test-model",
                    classified_at=datetime.now(UTC),
                    moderation_status="none",
                    notified=False,
                ),
            ]
        )
        db.session.commit()
        run = patrol_repo.create_patrol_run(user.id)
        return user.id, run.id


def test_build_notification_groups_alerts_and_escapes_preview(app):
    user_id, run_id = _seed_alert_data(app)

    with app.app_context():
        plans = build_notification_plans(
            user_id=user_id,
            owner_channel_id="UC_NOTIFICATION_OWNER",
            patrol_run_id=run_id,
            video_ids=["video-notification"],
            web_base_url="https://example.test/",
            default_min_alert_count=1,
        )

    assert len(plans) == 1
    plan = plans[0]
    assert plan.comment_ids == ("alert-review", "alert-judol")
    assert plan.judol_count == 1
    assert plan.review_count == 1
    assert "&lt;b&gt;info link gacor&lt;/b&gt;" in plan.message_html
    assert "&lt;Video &amp; Judol&gt;" in plan.message_html
    assert plan.review_url == "https://example.test/videos/video-notification"


def test_dispatch_marks_comments_only_after_success(app):
    user_id, run_id = _seed_alert_data(app)
    with app.app_context():
        plans = build_notification_plans(
            user_id=user_id,
            owner_channel_id="UC_NOTIFICATION_OWNER",
            patrol_run_id=run_id,
            video_ids=["video-notification"],
            web_base_url="https://example.test",
            default_min_alert_count=1,
        )

    bot = _FakeBot()
    result = asyncio.run(
        dispatch_notifications(
            app=app,
            bot=bot,
            plans=plans,
            rate_limiter=TelegramRateLimiter(10),
        )
    )

    assert result.sent == 1
    assert result.failed == 0
    assert bot.messages[0]["chat_id"] == 123456789
    assert bot.messages[0]["parse_mode"] == "HTML"
    with app.app_context():
        comments = db.session.query(Comment).filter(Comment.video_id == "video-notification").all()
        assert all(comment.notified for comment in comments if comment.zone in {"judol", "review"})
        assert not db.session.get(Comment, "normal-comment").notified
        run = db.session.get(PatrolRun, run_id)
        assert run.alerts_sent == 1
        assert build_notification_plans(
            user_id=user_id,
            owner_channel_id="UC_NOTIFICATION_OWNER",
            patrol_run_id=run_id,
            video_ids=["video-notification"],
            web_base_url="https://example.test",
            default_min_alert_count=1,
        ) == []


def test_dispatch_failure_keeps_comments_pending(app):
    user_id, run_id = _seed_alert_data(app)
    with app.app_context():
        plans = build_notification_plans(
            user_id=user_id,
            owner_channel_id="UC_NOTIFICATION_OWNER",
            patrol_run_id=run_id,
            video_ids=["video-notification"],
            web_base_url="https://example.test",
            default_min_alert_count=1,
        )

    result = asyncio.run(
        dispatch_notifications(
            app=app,
            bot=_FakeBot(fail=True),
            plans=plans,
            rate_limiter=TelegramRateLimiter(10),
        )
    )

    assert result.sent == 0
    assert result.failed == 1
    with app.app_context():
        assert db.session.get(Comment, "alert-judol").notified is False
        assert db.session.get(Comment, "alert-review").notified is False


def test_threshold_blocks_judol_below_minimum_but_allows_review(app):
    user_id, run_id = _seed_alert_data(app, min_alert_count=2)

    with app.app_context():
        plans = build_notification_plans(
            user_id=user_id,
            owner_channel_id="UC_NOTIFICATION_OWNER",
            patrol_run_id=run_id,
            video_ids=["video-notification"],
            web_base_url="https://example.test",
            default_min_alert_count=1,
        )

    assert len(plans) == 1
    assert plans[0].review_count == 1


def test_rate_limiter_is_applied_per_chat():
    limiter = TelegramRateLimiter(1)
    now = datetime(2026, 11, 26, 12, 0, tzinfo=UTC)

    assert limiter.allow(100, now=now) is True
    assert limiter.allow(100, now=now + timedelta(seconds=1)) is False
    assert limiter.allow(200, now=now) is True
    assert limiter.allow(100, now=now + timedelta(seconds=61)) is True


def test_forbidden_chat_is_paused(app):
    user_id, run_id = _seed_alert_data(app)
    with app.app_context():
        plans = build_notification_plans(
            user_id=user_id,
            owner_channel_id="UC_NOTIFICATION_OWNER",
            patrol_run_id=run_id,
            video_ids=["video-notification"],
            web_base_url="https://example.test",
            default_min_alert_count=1,
        )

    result = asyncio.run(
        dispatch_notifications(
            app=app,
            bot=_ForbiddenBot(),
            plans=plans,
            rate_limiter=TelegramRateLimiter(10),
        )
    )

    assert result.sent == 0
    assert result.failed == 1
    with app.app_context():
        link = db.session.query(TelegramLink).filter_by(user_id=user_id).one()
        assert link.paused is True
