"""Uji sinkronisasi daftar video YouTube ke tabel `videos`."""

from __future__ import annotations

from datetime import UTC, datetime

from app.extensions import db
from app.models import Video
from app.services.session_store import session_store


def _authenticate(client, channel_id: str = "UC_VIDEO_OWNER") -> None:
    server_session = session_store.create(
        channel_id=channel_id,
        channel_title="Pemilik Video",
        email="owner@example.com",
        access_token="fake-access-token",
    )
    with client.session_transaction() as flask_session:
        flask_session["sid"] = server_session.sid


def test_list_videos_requires_login(client):
    response = client.get("/api/videos")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_list_videos_fetches_and_persists_cache(client, app, monkeypatch):
    _authenticate(client)
    videos = [
        {
            "video_id": "video-001",
            "title": "Video Pertama",
            "thumbnail_url": "https://img.example/1.jpg",
            "published_at": datetime(2026, 11, 20, tzinfo=UTC),
            "comment_count": 12,
        },
        {
            "video_id": "video-002",
            "title": "Video Kedua",
            "thumbnail_url": "https://img.example/2.jpg",
            "published_at": datetime(2026, 11, 19, tzinfo=UTC),
            "comment_count": 3,
        },
    ]
    monkeypatch.setattr(
        "app.blueprints.videos.fetch_uploads_playlist_id",
        lambda *args: "uploads-playlist-001",
    )
    monkeypatch.setattr("app.blueprints.videos.fetch_channel_videos", lambda *args, **kwargs: videos)

    response = client.get("/api/videos?page_size=1")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["total"] == 2
    assert data["total_pages"] == 2
    assert data["items"][0]["video_id"] == "video-001"
    assert data["refreshed"] is True
    assert data["synced_count"] == 2
    assert data["sync_mode"] == "initial"
    assert data["new_videos"] == 2

    with app.app_context():
        stored = db.session.get(Video, "video-001")
        assert stored is not None
        assert stored.owner_channel_id == "UC_VIDEO_OWNER"
        assert stored.comment_count == 12

    response = client.get("/api/videos?page=2&page_size=1")
    assert response.status_code == 200
    assert response.get_json()["data"]["items"][0]["video_id"] == "video-002"


def test_list_videos_uses_fresh_database_cache(client, monkeypatch):
    _authenticate(client, "UC_CACHE_OWNER")
    videos = [
        {
            "video_id": "cached-video",
            "title": "Video Cached",
            "thumbnail_url": "",
            "published_at": datetime(2026, 11, 20, tzinfo=UTC),
            "comment_count": 1,
        }
    ]
    monkeypatch.setattr(
        "app.blueprints.videos.fetch_uploads_playlist_id",
        lambda *args: "uploads-playlist-cache",
    )
    monkeypatch.setattr("app.blueprints.videos.fetch_channel_videos", lambda *args, **kwargs: videos)
    first = client.get("/api/videos")
    assert first.status_code == 200

    def should_not_fetch(*args, **kwargs):
        raise AssertionError("YouTube API tidak boleh dipanggil untuk cache yang masih fresh")

    monkeypatch.setattr("app.blueprints.videos.fetch_channel_videos", should_not_fetch)
    second = client.get("/api/videos")

    assert second.status_code == 200
    assert second.get_json()["data"]["refreshed"] is False
    assert second.get_json()["data"]["items"][0]["video_id"] == "cached-video"


def test_refresh_uses_incremental_sync_and_does_not_duplicate(client, app, monkeypatch):
    _authenticate(client, "UC_INCREMENTAL_OWNER")
    initial_video = {
        "video_id": "old-video",
        "title": "Video Lama",
        "thumbnail_url": "",
        "published_at": datetime(2026, 11, 18, tzinfo=UTC),
        "comment_count": 2,
    }
    new_video = {
        "video_id": "new-video",
        "title": "Video Baru",
        "thumbnail_url": "",
        "published_at": datetime(2026, 11, 20, tzinfo=UTC),
        "comment_count": 4,
    }
    updated_old_video = {
        **initial_video,
        "title": "Video Lama Diperbarui",
        "comment_count": 9,
    }
    monkeypatch.setattr(
        "app.blueprints.videos.fetch_uploads_playlist_id",
        lambda *args: "uploads-playlist-incremental",
    )
    monkeypatch.setattr(
        "app.blueprints.videos.fetch_channel_videos",
        lambda *args, **kwargs: [initial_video],
    )

    initial = client.get("/api/videos")
    assert initial.status_code == 200

    calls: list[set[str]] = []

    def incremental(*args, **kwargs):
        calls.append(args[2])
        return [new_video] if len(calls) == 1 else []

    monkeypatch.setattr("app.blueprints.videos.fetch_incremental_videos", incremental)
    monkeypatch.setattr(
        "app.blueprints.videos.fetch_video_metadata",
        lambda *args, **kwargs: [updated_old_video, new_video],
    )

    refreshed = client.get("/api/videos?refresh=true")
    assert refreshed.status_code == 200
    refreshed_data = refreshed.get_json()["data"]
    assert refreshed_data["sync_mode"] == "incremental"
    assert refreshed_data["new_videos"] == 1
    assert refreshed_data["updated_videos"] == 1
    assert refreshed_data["metadata_batches"] == 1
    assert refreshed_data["total"] == 2
    assert calls == [{"old-video"}]

    second_refresh = client.get("/api/videos?refresh=true")
    assert second_refresh.status_code == 200
    second_data = second_refresh.get_json()["data"]
    assert second_data["new_videos"] == 0
    assert second_data["updated_videos"] == 2
    assert second_data["total"] == 2

    with app.app_context():
        stored_old = db.session.get(Video, "old-video")
        stored_new = db.session.get(Video, "new-video")
        assert stored_old is not None
        assert stored_old.title == "Video Lama Diperbarui"
        assert stored_old.comment_count == 9
        assert stored_new is not None
