"""Uji algoritma incremental sync YouTube tanpa melakukan request jaringan."""

from __future__ import annotations

from app.services import youtube


def test_incremental_sync_stops_at_known_video_and_details_only_new_video(monkeypatch):
    calls: list[tuple[str, dict]] = []
    responses = [
        {
            "items": [
                {
                    "snippet": {
                        "title": "Video Baru",
                        "publishedAt": "2026-11-20T10:00:00Z",
                        "resourceId": {"videoId": "new-video"},
                        "thumbnails": {"default": {"url": "https://img.example/new.jpg"}},
                    }
                },
                {
                    "snippet": {
                        "title": "Video Lama",
                        "publishedAt": "2026-11-19T10:00:00Z",
                        "resourceId": {"videoId": "known-video"},
                    }
                },
            ],
            "nextPageToken": "must-not-be-requested",
        },
        {
            "items": [
                {
                    "id": "new-video",
                    "snippet": {
                        "title": "Video Baru",
                        "publishedAt": "2026-11-20T10:00:00Z",
                    },
                    "statistics": {"commentCount": "17"},
                }
            ]
        },
    ]

    def fake_get(endpoint: str, access_token: str, params: dict):
        calls.append((endpoint, params))
        return responses.pop(0)

    monkeypatch.setattr(youtube, "_get", fake_get)

    result = youtube.fetch_incremental_videos(
        "access-token",
        "uploads-playlist",
        {"known-video"},
    )

    assert [video["video_id"] for video in result] == ["new-video"]
    assert result[0]["comment_count"] == 17
    assert [endpoint for endpoint, _ in calls] == ["playlistItems", "videos"]
    assert calls[0][1]["maxResults"] == 50
    assert calls[1][1]["id"] == "new-video"
    assert responses == []


def test_comment_fetch_stops_at_existing_comment(monkeypatch):
    calls: list[tuple[str, dict]] = []
    responses = [
        {
            "items": [
                {
                    "id": "new-comment",
                    "snippet": {
                        "topLevelComment": {
                            "id": "new-comment",
                            "snippet": {
                                "authorDisplayName": "Spammer",
                                "authorChannelId": {"value": "UC_SPAM"},
                                "textOriginal": "info link gacor",
                                "publishedAt": "2026-11-20T10:00:00Z",
                                "likeCount": 4,
                            },
                        }
                    },
                },
                {
                    "id": "known-comment",
                    "snippet": {
                        "topLevelComment": {
                            "id": "known-comment",
                            "snippet": {
                                "authorDisplayName": "Penonton",
                                "textOriginal": "Komentar lama",
                            },
                        }
                    },
                },
            ],
            "nextPageToken": "must-not-be-requested",
        }
    ]

    def fake_get(endpoint: str, access_token: str, params: dict):
        calls.append((endpoint, params))
        return responses.pop(0)

    monkeypatch.setattr(youtube, "_get", fake_get)

    result = youtube.fetch_video_comments(
        "access-token",
        "video-001",
        {"known-comment"},
    )

    assert [comment["comment_id"] for comment in result.comments] == ["new-comment"]
    assert result.comments[0]["author_channel_id"] == "UC_SPAM"
    assert result.comments[0]["like_count"] == 4
    assert result.pages_fetched == 1
    assert result.stopped_on_existing is True
    assert calls[0][0] == "commentThreads"
    assert calls[0][1]["maxResults"] == 100
    assert calls[0][1]["order"] == "time"


def test_reject_comment_batch_sends_comma_separated_ids(monkeypatch):
    calls: list[dict] = []

    class FakeResponse:
        ok = True

    def fake_post(url: str, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr(youtube.requests, "post", fake_post)

    youtube.reject_comment_batch("access-token", ["comment-1", "comment-2"])

    assert calls[0]["url"].endswith("/comments/setModerationStatus")
    assert calls[0]["params"]["id"] == "comment-1,comment-2"
    assert calls[0]["params"]["moderationStatus"] == "rejected"
    assert calls[0]["headers"]["Authorization"] == "Bearer access-token"
