"""Uji preview, batching, status, log, dan estimasi kuota reject."""

from __future__ import annotations

from datetime import UTC, datetime

from app.extensions import db
from app.models import Comment, ModerationLog, Video
from app.services.session_store import session_store


def _authenticate(client, channel_id: str = "UC_MODERATION_OWNER") -> None:
    server_session = session_store.create(
        channel_id=channel_id,
        channel_title="Pemilik Moderasi",
        email="moderation@example.com",
        access_token="fake-access-token",
    )
    with client.session_transaction() as flask_session:
        flask_session["sid"] = server_session.sid


def _seed_comments(app, count: int = 2) -> list[str]:
    ids = [f"reject-comment-{index}" for index in range(count)]
    with app.app_context():
        db.session.add(
            Video(
                video_id="moderation-video",
                owner_channel_id="UC_MODERATION_OWNER",
                title="Video Moderasi",
                comment_count=count,
                published_at=datetime(2026, 11, 20, tzinfo=UTC),
            )
        )
        db.session.add_all(
            [
                Comment(
                    comment_id=comment_id,
                    video_id="moderation-video",
                    owner_channel_id="UC_MODERATION_OWNER",
                    author_name=f"Akun {index}",
                    text_original="info link gacor",
                    zone="judol",
                    score=0.9,
                    classified_at=datetime(2026, 11, 20, tzinfo=UTC),
                )
                for index, comment_id in enumerate(ids)
            ]
        )
        db.session.commit()
    return ids


def test_reject_preview_and_batch_updates_status_log_and_quota(client, app, monkeypatch):
    _authenticate(client)
    comment_ids = _seed_comments(app)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "app.blueprints.comments.reject_comment_batch",
        lambda token, ids: calls.append(ids),
    )

    preview = client.post(
        "/api/comments/reject/preview",
        json={"comment_ids": comment_ids},
    )
    assert preview.status_code == 200
    preview_data = preview.get_json()["data"]
    assert preview_data["estimate"]["comment_count"] == 2
    assert preview_data["estimate"]["batch_count"] == 1
    assert preview_data["estimate"]["estimated_quota_units"] == 50
    assert preview_data["estimate"]["sufficient"] is True

    response = client.post(
        "/api/comments/reject",
        json={"comment_ids": comment_ids, "confirmed": True},
    )
    assert response.status_code == 200
    summary = response.get_json()["data"]
    assert summary["succeeded"] == 2
    assert summary["failed"] == 0
    assert calls == [comment_ids]
    assert summary["quota"]["used_units"] == 50

    with app.app_context():
        rows = db.session.query(Comment).filter(Comment.comment_id.in_(comment_ids)).all()
        logs = db.session.query(ModerationLog).filter(ModerationLog.comment_id.in_(comment_ids)).all()
        assert {row.moderation_status for row in rows} == {"rejected"}
        assert len(logs) == 2

    detail = client.get("/api/videos/moderation-video")
    assert detail.status_code == 200
    detail_data = detail.get_json()["data"]
    assert detail_data["comment_count"] == 2
    assert detail_data["stored_comment_count"] == 0


def test_reject_all_judol_sends_two_batches_for_51_comments(client, app, monkeypatch):
    _authenticate(client)
    comment_ids = _seed_comments(app, count=51)
    batches: list[list[str]] = []
    monkeypatch.setattr(
        "app.blueprints.comments.reject_comment_batch",
        lambda token, ids: batches.append(ids),
    )

    response = client.post(
        "/api/comments/reject",
        json={"video_id": "moderation-video", "all_judol": True, "confirmed": True},
    )

    assert response.status_code == 200
    summary = response.get_json()["data"]
    assert summary["requested"] == 51
    assert summary["succeeded"] == 51
    assert summary["batch_count"] == 2
    assert summary["estimated_quota_units"] == 100
    assert [len(batch) for batch in batches] == [50, 1]
    assert set(comment_ids) == set(summary["rejected"])
