"""Uji baseline dan patroli incremental Sentinel tanpa request YouTube sungguhan."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.ml.loader import ClassificationResult
from app.models import Comment, MonitoredVideo, PatrolRun, TelegramLink, User, Video
from app.repositories import user_repo
from app.sentinel.patrol import _PATROL_LOCK, run_patrol_cycle
from app.services.google_token import AccessTokenResult, InvalidGrantError
from app.services.youtube import CommentFetchResult, YouTubeServiceError


def _seed_linked_user(app, channel_id: str, *, paused: bool = False) -> int:
    with app.app_context():
        user = user_repo.upsert_user(
            channel_id=channel_id,
            email=f"{channel_id}@example.com",
            refresh_token_plain="refresh-token",
        )
        db.session.add(
            TelegramLink(
                user_id=user.id,
                chat_id=abs(hash(channel_id)) % 10_000_000 + 1000,
                paused=paused,
            )
        )
        db.session.commit()
        return user.id


def _token_result() -> AccessTokenResult:
    return AccessTokenResult(
        access_token="access-token-test",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        expires_in=3600,
    )


def _select_video(
    app,
    user_id: int,
    channel_id: str,
    video_id: str,
    *,
    last_comment_count: int | None = None,
) -> None:
    with app.app_context():
        db.session.add(
            Video(
                video_id=video_id,
                owner_channel_id=channel_id,
                title=video_id,
                comment_count=last_comment_count or 0,
            )
        )
        db.session.add(
            MonitoredVideo(
                user_id=user_id,
                video_id=video_id,
                last_comment_count=last_comment_count,
                active=True,
            )
        )
        db.session.commit()


def test_first_cycle_creates_baseline_without_fetching_old_comments(app, monkeypatch):
    user_id = _seed_linked_user(app, "UC_PATROL_BASELINE")
    _select_video(app, user_id, "UC_PATROL_BASELINE", "video-baseline")
    monkeypatch.setattr(
        "app.sentinel.patrol.google_token.refresh_access_token",
        lambda app, user_id: _token_result(),
    )
    monkeypatch.setattr(
        "app.sentinel.patrol.youtube.fetch_video_metadata",
        lambda token, video_ids: [
            {
                "video_id": "video-baseline",
                "title": "Video baseline",
                "comment_count": 4,
            }
        ],
    )
    fetch_comments = []

    def should_not_fetch(*args, **kwargs):
        fetch_comments.append(True)
        raise AssertionError("baseline tidak boleh mengambil komentar lama")

    monkeypatch.setattr(
        "app.sentinel.patrol.youtube.fetch_video_comments",
        should_not_fetch,
    )

    result = run_patrol_cycle(app)

    assert result.users_checked == 1
    assert result.videos_checked == 1
    assert result.new_comments == 0
    assert fetch_comments == []
    with app.app_context():
        monitored = db.session.query(MonitoredVideo).one()
        assert monitored.user_id == user_id
        assert monitored.last_comment_count == 4
        assert monitored.last_checked_at is not None
        assert db.session.query(Comment).count() == 0
        patrol_run = db.session.query(PatrolRun).one()
        assert patrol_run.est_api_units == 1
        assert patrol_run.error is None


def test_unchanged_count_skips_comment_api_and_changed_count_is_incremental(
    app,
    monkeypatch,
):
    _seed_linked_user(app, "UC_PATROL_INCREMENTAL")
    with app.app_context():
        user = db.session.query(User).filter_by(channel_id="UC_PATROL_INCREMENTAL").one()
        user_id = user.id
    _select_video(app, user_id, "UC_PATROL_INCREMENTAL", "video-incremental")
    count = {"value": 2}
    monkeypatch.setattr(
        "app.sentinel.patrol.google_token.refresh_access_token",
        lambda app, user_id: _token_result(),
    )
    monkeypatch.setattr(
        "app.sentinel.patrol.youtube.fetch_video_metadata",
        lambda token, video_ids: [
            {"video_id": "video-incremental", "title": "Video", "comment_count": count["value"]}
        ],
    )
    comment_calls: list[str] = []

    def fake_fetch_comments(
        *,
        access_token,
        video_id,
        known_comment_ids,
        max_comments,
        max_pages,
    ):
        comment_calls.append(video_id)
        return CommentFetchResult(
            comments=[
                {
                    "comment_id": "comment-new",
                    "author_name": "Tester",
                    "text_original": "komentar baru",
                    "like_count": 0,
                }
            ],
            pages_fetched=1,
            stopped_on_existing=False,
        )

    monkeypatch.setattr(
        "app.sentinel.patrol.youtube.fetch_video_comments",
        fake_fetch_comments,
    )
    class FakeRegistry:
        def classify_array(self, texts):
            assert texts == ["komentar baru"]
            return [
                ClassificationResult(
                    text_prepared="komentar baru",
                    text_hash="c" * 64,
                    score=0.91,
                    zone="judol",
                    rule_hit=False,
                    model_version="test-model",
                )
            ]

    monkeypatch.setattr(
        "app.services.comment_classifier.get_registry",
        lambda: FakeRegistry(),
    )

    run_patrol_cycle(app)
    run_patrol_cycle(app)
    assert comment_calls == []

    count["value"] = 3
    result = run_patrol_cycle(app)

    assert result.new_comments == 1
    assert comment_calls == ["video-incremental"]
    with app.app_context():
        monitored = db.session.query(MonitoredVideo).one()
        assert monitored.last_comment_count == 3
        comment = db.session.query(Comment).one()
        assert comment.comment_id == "comment-new"
        assert comment.zone == "judol"
        assert comment.model_version == "test-model"
        assert comment.notified is False
        assert db.session.query(PatrolRun).count() == 3


def test_paused_user_is_skipped(app, monkeypatch):
    _seed_linked_user(app, "UC_PATROL_PAUSED", paused=True)
    refresh_calls = []

    def should_not_refresh(*args, **kwargs):
        refresh_calls.append(True)
        raise AssertionError("user paused tidak boleh refresh token")

    monkeypatch.setattr(
        "app.sentinel.patrol.google_token.refresh_access_token",
        should_not_refresh,
    )

    result = run_patrol_cycle(app)

    assert result.users_checked == 0
    assert refresh_calls == []
    with app.app_context():
        assert db.session.query(PatrolRun).count() == 0


def test_invalid_grant_pauses_user_and_records_run(app, monkeypatch):
    user_id = _seed_linked_user(app, "UC_PATROL_INVALID_GRANT")

    def invalid_grant(app, user_id):
        raise InvalidGrantError()

    monkeypatch.setattr(
        "app.sentinel.patrol.google_token.refresh_access_token",
        invalid_grant,
    )

    result = run_patrol_cycle(app)

    assert result.users_checked == 1
    assert result.errors
    with app.app_context():
        link = db.session.query(TelegramLink).filter_by(user_id=user_id).one()
        assert link.paused is True
        patrol_run = db.session.query(PatrolRun).one()
        assert "invalid_grant" in (patrol_run.error or "")


def test_user_and_video_errors_are_isolated(app, monkeypatch):
    first_user_id = _seed_linked_user(app, "UC_PATROL_ERROR")
    second_user_id = _seed_linked_user(app, "UC_PATROL_OK")
    _select_video(app, first_user_id, "UC_PATROL_ERROR", "video-error")
    _select_video(app, second_user_id, "UC_PATROL_OK", "video-ok")

    def fetch_metadata(token, video_ids):
        if token == f"token-{first_user_id}":
            raise YouTubeServiceError("youtube_unavailable", "network")
        return [{"video_id": "video-ok", "title": "OK", "comment_count": 1}]

    def refresh_with_user(app, user_id):
        return AccessTokenResult(
            access_token=f"token-{user_id}",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            expires_in=3600,
        )

    monkeypatch.setattr(
        "app.sentinel.patrol.google_token.refresh_access_token",
        refresh_with_user,
    )
    monkeypatch.setattr(
        "app.sentinel.patrol.youtube.fetch_video_metadata",
        fetch_metadata,
    )

    result = run_patrol_cycle(app)

    assert result.users_checked == 2
    assert result.videos_checked == 1
    with app.app_context():
        assert db.session.query(PatrolRun).count() == 2
        assert db.session.query(MonitoredVideo).filter_by(user_id=second_user_id).count() == 1
        assert db.session.query(MonitoredVideo).filter_by(user_id=first_user_id).count() == 1


def test_existing_video_owned_by_other_user_is_not_reassigned(app, monkeypatch):
    first_user_id = _seed_linked_user(app, "UC_PATROL_OWNER_A")
    second_user_id = _seed_linked_user(app, "UC_PATROL_OWNER_B")
    with app.app_context():
        owner_b = db.session.get(User, second_user_id)
        db.session.add(Video(video_id="shared-video", owner_channel_id=owner_b.channel_id))
        db.session.add(
            MonitoredVideo(
                user_id=first_user_id,
                video_id="shared-video",
                active=True,
            )
        )
        db.session.commit()

    monkeypatch.setattr(
        "app.sentinel.patrol.google_token.refresh_access_token",
        lambda app, user_id: _token_result(),
    )
    monkeypatch.setattr(
        "app.sentinel.patrol.youtube.fetch_video_metadata",
        lambda token, video_ids: [
            {"video_id": "shared-video", "title": "Shared", "comment_count": 1}
        ],
    )

    run_patrol_cycle(app)

    with app.app_context():
        video = db.session.get(Video, "shared-video")
        assert video.owner_channel_id == "UC_PATROL_OWNER_B"
        assert db.session.query(MonitoredVideo).filter_by(user_id=first_user_id).count() == 1


def test_patrol_cycle_skips_when_another_cycle_holds_lock(app):
    assert _PATROL_LOCK.acquire(blocking=False)
    try:
        result = run_patrol_cycle(app)
    finally:
        _PATROL_LOCK.release()

    assert result.skipped_locked is True
