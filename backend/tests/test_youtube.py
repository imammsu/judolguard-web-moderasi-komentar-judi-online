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
