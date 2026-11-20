"""Client YouTube Data API v3 untuk sinkronisasi video dan komentar."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_REQUEST_TIMEOUT = 20
PLAYLIST_PAGE_SIZE = 50
VIDEO_BATCH_SIZE = 50
COMMENT_PAGE_SIZE = 100


class YouTubeServiceError(Exception):
    """Error yang aman diteruskan sebagai respons API aplikasi."""

    def __init__(self, code: str, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _thumbnail_url(snippet: dict[str, Any]) -> str:
    thumbnails = snippet.get("thumbnails") or {}
    for size in ("high", "medium", "default"):
        thumbnail = thumbnails.get(size) or {}
        if thumbnail.get("url"):
            return str(thumbnail["url"])
    return ""


def _error_from_response(response: requests.Response) -> YouTubeServiceError:
    payload: dict[str, Any] = {}
    with suppress(ValueError):
        payload = response.json()

    errors = (payload.get("error") or {}).get("errors") or []
    reason = str(errors[0].get("reason", "")) if errors else ""

    if response.status_code == 401:
        return YouTubeServiceError(
            "youtube_token_expired",
            "Sesi YouTube telah kedaluwarsa. Silakan login kembali.",
            401,
        )
    if reason in {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}:
        return YouTubeServiceError(
            "youtube_quota_exceeded",
            "Kuota YouTube API sedang habis. Coba lagi nanti.",
            429,
        )
    if reason == "commentsDisabled":
        return YouTubeServiceError(
            "comments_disabled",
            "Komentar pada video ini dinonaktifkan oleh pemilik channel.",
            422,
        )
    if reason == "videoNotFound":
        return YouTubeServiceError(
            "youtube_video_not_found",
            "Video tidak ditemukan atau tidak dapat diakses.",
            404,
        )
    if response.status_code == 403:
        return YouTubeServiceError(
            "youtube_forbidden",
            "Akses YouTube API ditolak. Pastikan izin channel sudah diberikan.",
            403,
        )
    return YouTubeServiceError(
        "youtube_api_error",
        f"YouTube API mengembalikan HTTP {response.status_code}.",
        502,
    )


def _get(endpoint: str, access_token: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(
            f"{YOUTUBE_API_BASE}/{endpoint}",
            params=params,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept-Encoding": "gzip",
                "User-Agent": "JudolGuard/0.4 (gzip)",
            },
            timeout=YOUTUBE_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise YouTubeServiceError(
            "youtube_unavailable",
            "YouTube API tidak dapat dihubungi. Coba lagi beberapa saat.",
            502,
        ) from exc

    if not response.ok:
        raise _error_from_response(response)

    try:
        payload = response.json()
    except ValueError as exc:
        raise YouTubeServiceError(
            "youtube_invalid_response",
            "Respons dari YouTube API tidak valid.",
            502,
        ) from exc

    if not isinstance(payload, dict):
        raise YouTubeServiceError(
            "youtube_invalid_response",
            "Respons dari YouTube API tidak valid.",
            502,
        )
    return payload


@dataclass(frozen=True)
class CommentFetchResult:
    comments: list[dict[str, Any]]
    pages_fetched: int
    stopped_on_existing: bool


def _comment_from_thread(item: dict[str, Any]) -> dict[str, Any] | None:
    thread_snippet = item.get("snippet") or {}
    top_level = thread_snippet.get("topLevelComment") or {}
    comment_id = top_level.get("id") or item.get("id")
    if not comment_id:
        return None

    snippet = top_level.get("snippet") or {}
    author_channel = snippet.get("authorChannelId") or {}
    text = snippet.get("textOriginal") or snippet.get("textDisplay") or ""
    return {
        "comment_id": str(comment_id),
        "author_name": str(snippet.get("authorDisplayName") or ""),
        "author_channel_id": str(author_channel.get("value") or "") or None,
        "text_original": str(text),
        "published_at": _parse_datetime(snippet.get("publishedAt")),
        "like_count": int(snippet.get("likeCount") or 0),
    }


def fetch_video_comments(
    access_token: str,
    video_id: str,
    known_comment_ids: set[str],
    max_comments: int = 2000,
    max_pages: int = 20,
) -> CommentFetchResult:
    """Ambil komentar top-level terbaru secara incremental."""
    if not access_token:
        raise YouTubeServiceError(
            "youtube_unauthorized",
            "Token YouTube tidak tersedia. Silakan login kembali.",
            401,
        )
    if not video_id or max_comments < 1 or max_pages < 1:
        return CommentFetchResult([], 0, False)

    comments: list[dict[str, Any]] = []
    page_token: str | None = None
    stopped_on_existing = False
    pages_fetched = 0

    for _ in range(max_pages):
        params: dict[str, Any] = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(COMMENT_PAGE_SIZE, max_comments - len(comments)),
            "order": "time",
            "textFormat": "plainText",
            "fields": (
                "nextPageToken,"
                "items(id,snippet/topLevelComment(id,snippet("
                "authorDisplayName,authorChannelId/value,textOriginal,textDisplay,publishedAt,likeCount)))"
            ),
        }
        if page_token:
            params["pageToken"] = page_token

        payload = _get("commentThreads", access_token, params)
        pages_fetched += 1
        for item in payload.get("items") or []:
            comment = _comment_from_thread(item)
            if comment is None:
                continue
            if comment["comment_id"] in known_comment_ids:
                stopped_on_existing = True
                break
            comments.append(comment)
            if len(comments) >= max_comments:
                break

        if stopped_on_existing or len(comments) >= max_comments:
            break
        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    return CommentFetchResult(
        comments=comments,
        pages_fetched=pages_fetched,
        stopped_on_existing=stopped_on_existing,
    )


def _fetch_uploads_playlist_id(access_token: str) -> str:
    payload = _get(
        "channels",
        access_token,
        {
            "part": "contentDetails",
            "mine": "true",
            "fields": "items(contentDetails/relatedPlaylists/uploads)",
        },
    )
    items = payload.get("items") or []
    if not items:
        raise YouTubeServiceError(
            "youtube_channel_not_found",
            "Channel YouTube tidak ditemukan untuk akun ini.",
            404,
        )

    uploads_id = ((items[0].get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")
    if not uploads_id:
        raise YouTubeServiceError(
            "youtube_uploads_playlist_missing",
            "Playlist video channel tidak ditemukan.",
            502,
        )
    return str(uploads_id)


def fetch_uploads_playlist_id(access_token: str) -> str:
    """Ambil ID playlist uploads channel yang sedang login."""
    if not access_token:
        raise YouTubeServiceError(
            "youtube_unauthorized",
            "Token YouTube tidak tersedia. Silakan login kembali.",
            401,
        )
    return _fetch_uploads_playlist_id(access_token)


def _playlist_item_to_video(item: dict[str, Any]) -> dict[str, Any] | None:
    snippet = item.get("snippet") or {}
    resource_id = snippet.get("resourceId") or {}
    video_id = resource_id.get("videoId")
    if not video_id:
        return None
    return {
        "video_id": str(video_id),
        "title": str(snippet.get("title") or "Video tanpa judul"),
        "thumbnail_url": _thumbnail_url(snippet),
        "published_at": _parse_datetime(snippet.get("publishedAt")),
    }


def _fetch_playlist_items(
    access_token: str,
    uploads_playlist_id: str,
    max_videos: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_token: str | None = None

    while len(items) < max_videos:
        params: dict[str, Any] = {
            "part": "snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": min(PLAYLIST_PAGE_SIZE, max_videos - len(items)),
        }
        if page_token:
            params["pageToken"] = page_token

        payload = _get("playlistItems", access_token, params)
        for item in payload.get("items") or []:
            video = _playlist_item_to_video(item)
            if video is None:
                continue
            items.append(video)
            if len(items) >= max_videos:
                break

        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    return items


def _fetch_new_playlist_items(
    access_token: str,
    uploads_playlist_id: str,
    known_video_ids: set[str],
    max_new_videos: int,
    max_pages: int,
) -> list[dict[str, Any]]:
    """Ambil item terbaru sampai menemukan video yang sudah ada di database."""
    new_items: list[dict[str, Any]] = []
    seen_new_ids: set[str] = set()
    page_token: str | None = None

    for _ in range(max_pages):
        params: dict[str, Any] = {
            "part": "snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": PLAYLIST_PAGE_SIZE,
        }
        if page_token:
            params["pageToken"] = page_token

        payload = _get("playlistItems", access_token, params)
        encountered_known_video = False
        for item in payload.get("items") or []:
            video = _playlist_item_to_video(item)
            if video is None:
                continue
            video_id = video["video_id"]
            if video_id in known_video_ids:
                encountered_known_video = True
                break
            if video_id not in seen_new_ids:
                new_items.append(video)
                seen_new_ids.add(video_id)
            if len(new_items) >= max_new_videos:
                break

        if encountered_known_video or len(new_items) >= max_new_videos:
            break
        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    return new_items


def _fetch_video_details(access_token: str, video_ids: list[str]) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    for start in range(0, len(video_ids), VIDEO_BATCH_SIZE):
        batch = video_ids[start : start + VIDEO_BATCH_SIZE]
        payload = _get(
            "videos",
            access_token,
            {
                "part": "snippet,statistics",
                "id": ",".join(batch),
            },
        )
        for item in payload.get("items") or []:
            video_id = str(item.get("id") or "")
            if not video_id:
                continue
            snippet = item.get("snippet") or {}
            statistics = item.get("statistics") or {}
            details[video_id] = {
                "title": str(snippet.get("title") or "Video tanpa judul"),
                "thumbnail_url": _thumbnail_url(snippet),
                "published_at": _parse_datetime(snippet.get("publishedAt")),
                "comment_count": int(statistics.get("commentCount") or 0),
            }
    return details


def _merge_video_details(
    playlist_items: list[dict[str, Any]],
    details: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    videos: list[dict[str, Any]] = []
    for item in playlist_items:
        detail = details.get(item["video_id"], {})
        videos.append(
            {
                **item,
                "title": detail.get("title") or item["title"],
                "thumbnail_url": detail.get("thumbnail_url") or item["thumbnail_url"],
                "published_at": detail.get("published_at") or item["published_at"],
                "comment_count": int(detail.get("comment_count") or 0),
            }
        )
    return videos


def fetch_channel_videos(
    access_token: str,
    max_videos: int = 500,
    uploads_playlist_id: str | None = None,
) -> list[dict[str, Any]]:
    """Ambil video channel dari uploads playlist dan lengkapi jumlah komentar."""
    if not access_token:
        raise YouTubeServiceError(
            "youtube_unauthorized",
            "Token YouTube tidak tersedia. Silakan login kembali.",
            401,
        )
    if max_videos < 1:
        return []

    uploads_playlist_id = uploads_playlist_id or _fetch_uploads_playlist_id(access_token)
    playlist_items = _fetch_playlist_items(access_token, uploads_playlist_id, max_videos)
    if not playlist_items:
        return []

    details = _fetch_video_details(access_token, [item["video_id"] for item in playlist_items])
    return _merge_video_details(playlist_items, details)


def fetch_incremental_videos(
    access_token: str,
    uploads_playlist_id: str,
    known_video_ids: set[str],
    max_new_videos: int = 100,
    max_pages: int = 10,
    include_details: bool = True,
) -> list[dict[str, Any]]:
    """Ambil hanya video baru dari bagian terbaru uploads playlist."""
    if not access_token:
        raise YouTubeServiceError(
            "youtube_unauthorized",
            "Token YouTube tidak tersedia. Silakan login kembali.",
            401,
        )
    if not uploads_playlist_id or max_new_videos < 1 or max_pages < 1:
        return []

    playlist_items = _fetch_new_playlist_items(
        access_token,
        uploads_playlist_id,
        known_video_ids,
        max_new_videos,
        max_pages,
    )
    if not playlist_items:
        return []
    if not include_details:
        return playlist_items

    details = _fetch_video_details(access_token, [item["video_id"] for item in playlist_items])
    return _merge_video_details(playlist_items, details)


def fetch_video_metadata(
    access_token: str,
    video_ids: set[str] | list[str],
) -> list[dict[str, Any]]:
    """Ambil metadata terbaru video dalam batch maksimal 50 ID per request."""
    if not access_token:
        raise YouTubeServiceError(
            "youtube_unauthorized",
            "Token YouTube tidak tersedia. Silakan login kembali.",
            401,
        )

    clean_ids = list(dict.fromkeys(str(video_id) for video_id in video_ids if video_id))
    if not clean_ids:
        return []

    details = _fetch_video_details(access_token, clean_ids)
    return [
        {
            "video_id": video_id,
            **detail,
        }
        for video_id, detail in details.items()
    ]
