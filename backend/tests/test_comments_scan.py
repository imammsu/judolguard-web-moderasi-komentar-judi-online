"""Uji endpoint Scan & Klasifikasi dan daftar komentar."""

from __future__ import annotations

from datetime import UTC, datetime

from app.extensions import db
from app.ml.loader import ClassificationResult
from app.models import Video
from app.services.session_store import session_store
from app.services.youtube import CommentFetchResult


def _authenticate(client, channel_id: str = "UC_COMMENT_OWNER") -> None:
    server_session = session_store.create(
        channel_id=channel_id,
        channel_title="Pemilik Video",
        email="owner@example.com",
        access_token="fake-access-token",
    )
    with client.session_transaction() as flask_session:
        flask_session["sid"] = server_session.sid


def _create_video(app, video_id: str = "video-comments") -> None:
    with app.app_context():
        db.session.add(
            Video(
                video_id=video_id,
                owner_channel_id="UC_COMMENT_OWNER",
                title="Video Komentar",
                thumbnail_url="",
                comment_count=2,
                published_at=datetime(2026, 11, 20, tzinfo=UTC),
            )
        )
        db.session.commit()


def test_scan_fetches_persists_and_classifies_comments(client, app, monkeypatch):
    _authenticate(client)
    _create_video(app)
    comments = [
        {
            "comment_id": "comment-judol",
            "author_name": "Akun Spam",
            "author_channel_id": "UC_SPAM",
            "text_original": "info link gacor",
            "published_at": datetime(2026, 11, 20, tzinfo=UTC),
            "like_count": 3,
        },
        {
            "comment_id": "comment-normal",
            "author_name": "Penonton",
            "author_channel_id": "UC_VIEWER",
            "text_original": "Videonya bagus",
            "published_at": datetime(2026, 11, 19, tzinfo=UTC),
            "like_count": 1,
        },
    ]
    monkeypatch.setattr(
        "app.services.jobs.fetch_video_comments",
        lambda *args, **kwargs: CommentFetchResult(comments, 1, False),
    )

    class FakeRegistry:
        def classify_array(self, texts):
            assert texts == ["Videonya bagus", "info link gacor"]
            return [
                ClassificationResult("videonya bagus", "b" * 64, 0.01, "bukan", False, "test-model"),
                ClassificationResult("info link gacor", "a" * 64, 0.12, "review", True, "test-model"),
            ]

    monkeypatch.setattr("app.services.jobs.get_registry", lambda: FakeRegistry())

    response = client.post("/api/videos/video-comments/scan")

    assert response.status_code == 202
    job = response.get_json()["data"]
    assert job["status"] == "done"
    assert job["progress"] == 100
    assert job["processed"] == 2

    comments_response = client.get("/api/videos/video-comments/comments?sort=score_desc")
    assert comments_response.status_code == 200
    data = comments_response.get_json()["data"]
    assert data["total"] == 2
    assert data["items"][0]["zone"] == "review"
    assert data["items"][0]["rule_hit"] is True
    assert data["items"][1]["zone"] == "bukan"


def test_scan_unknown_video_returns_404(client):
    _authenticate(client, "UC_COMMENT_OWNER")

    response = client.post("/api/videos/missing-video/scan")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "video_not_found"
