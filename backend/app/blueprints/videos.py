"""Endpoint daftar video channel (Part 4 tahap awal)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import ceil

from flask import Blueprint, current_app, g, request

from ..auth_guard import login_required
from ..extensions import db
from ..repositories import comment_repo, job_repo, meta_repo, video_repo
from ..responses import fail, ok
from ..services.jobs import submit_scan_job
from ..services.youtube import (
    YouTubeServiceError,
    fetch_channel_videos,
    fetch_incremental_videos,
    fetch_uploads_playlist_id,
    fetch_video_metadata,
)

bp = Blueprint("videos", __name__, url_prefix="/api/videos")


def _positive_int(value: str | None, default: int, maximum: int) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, 1), maximum)


def _as_bool(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def _needs_refresh(owner_channel_id: str, force: bool) -> bool:
    if video_repo.count_videos(owner_channel_id) == 0:
        return True
    latest = video_repo.get_latest_fetched_at(owner_channel_id)
    retention_days = int(current_app.config.get("DATA_RETENTION_DAYS", 30))
    if latest is None:
        return True
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    return latest < datetime.now(UTC) - timedelta(days=retention_days)


def _get_or_fetch_uploads_playlist_id(owner_channel_id: str, access_token: str) -> str:
    metadata = meta_repo.get_video_sync_meta(owner_channel_id)
    playlist_id = str(metadata.get("uploads_playlist_id") or "")
    if playlist_id:
        return playlist_id

    playlist_id = fetch_uploads_playlist_id(access_token)
    meta_repo.set_video_sync_meta(
        owner_channel_id,
        {
            **metadata,
            "uploads_playlist_id": playlist_id,
        },
    )
    return playlist_id


def _set_sync_timestamp(owner_channel_id: str, **extra: object) -> None:
    metadata = meta_repo.get_video_sync_meta(owner_channel_id)
    meta_repo.set_video_sync_meta(
        owner_channel_id,
        {
            **metadata,
            **extra,
            "last_checked_at": datetime.now(UTC).isoformat(),
        },
    )


def _serialize_video(
    video,
    *,
    stored_comment_count: int = 0,
    scan_status: str = "not_scanned",
) -> dict[str, object]:
    return {
        "video_id": video.video_id,
        "title": video.title,
        "thumbnail_url": video.thumbnail_url,
        "published_at": video.published_at.isoformat() if video.published_at else None,
        "comment_count": video.comment_count,
        "stored_comment_count": stored_comment_count,
        "scan_status": scan_status,
        "last_fetched_at": video.last_fetched_at.isoformat() if video.last_fetched_at else None,
    }


def _serialize_job(job) -> dict[str, object]:
    return {
        "id": str(job.id),
        "type": job.type,
        "video_id": job.video_id,
        "status": job.status,
        "progress": job.progress,
        "total": job.total,
        "processed": job.processed,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@bp.get("")
@login_required
def list_videos():
    owner_channel_id = g.owner_channel_id
    page = _positive_int(request.args.get("page"), 1, 10_000)
    page_size = _positive_int(request.args.get("page_size"), 12, 50)
    force_refresh = _as_bool(request.args.get("refresh"))
    existing_count = video_repo.count_videos(owner_channel_id)
    sync_mode = "cache"
    synced_count = 0
    new_videos = 0
    updated_videos = 0
    metadata_batches = 0
    estimated_quota = 0

    if _needs_refresh(owner_channel_id, False):
        try:
            playlist_id = _get_or_fetch_uploads_playlist_id(owner_channel_id, g.current_user.access_token)
            videos = fetch_channel_videos(
                g.current_user.access_token,
                max_videos=int(current_app.config.get("MAX_VIDEOS_PER_SYNC", 500)),
                uploads_playlist_id=playlist_id,
            )
            synced_count = video_repo.bulk_upsert_videos(owner_channel_id, videos)
            _set_sync_timestamp(owner_channel_id, last_full_sync_at=datetime.now(UTC).isoformat())
            sync_mode = "initial" if existing_count == 0 else "full_refresh"
            new_videos = len(videos) if existing_count == 0 else 0
            updated_videos = len(videos) if existing_count > 0 else 0
            metadata_batches = ceil(len(videos) / 50) if videos else 0
            estimated_quota = 1 + metadata_batches
        except YouTubeServiceError as exc:
            return fail(exc.code, exc.message, exc.status)
    elif force_refresh:
        try:
            playlist_id = _get_or_fetch_uploads_playlist_id(owner_channel_id, g.current_user.access_token)
            known_video_ids = video_repo.get_video_ids(owner_channel_id)
            new_video_items = fetch_incremental_videos(
                g.current_user.access_token,
                playlist_id,
                known_video_ids,
                max_new_videos=int(current_app.config.get("MAX_NEW_VIDEOS_PER_SYNC", 100)),
                max_pages=int(current_app.config.get("MAX_INCREMENTAL_PAGES", 10)),
                include_details=False,
            )
            new_video_ids = {item["video_id"] for item in new_video_items}
            all_video_ids = known_video_ids | new_video_ids
            refreshed_metadata = fetch_video_metadata(
                g.current_user.access_token,
                all_video_ids,
            )
            metadata_by_id = {item["video_id"]: item for item in refreshed_metadata}
            # Fallback agar playlist item baru tetap bisa disimpan jika detail API
            # tidak mengembalikan salah satu ID.
            all_metadata = [
                metadata_by_id.get(item["video_id"], item)
                for item in new_video_items
            ]
            all_metadata.extend(
                item for item in refreshed_metadata if item["video_id"] in known_video_ids
            )
            synced_count = video_repo.bulk_upsert_videos(owner_channel_id, all_metadata)
            new_videos = len(new_video_items)
            updated_videos = sum(1 for item in refreshed_metadata if item["video_id"] in known_video_ids)
            metadata_batches = ceil(len(all_video_ids) / 50) if all_video_ids else 0
            estimated_quota = 1 + metadata_batches
            _set_sync_timestamp(owner_channel_id)
            sync_mode = "incremental"
        except YouTubeServiceError as exc:
            return fail(exc.code, exc.message, exc.status)

    total = video_repo.count_videos(owner_channel_id)
    total_pages = ceil(total / page_size) if total else 0
    if total_pages and page > total_pages:
        page = total_pages

    videos = video_repo.list_videos(owner_channel_id, page, page_size)
    video_ids = [video.video_id for video in videos]
    stored_counts = comment_repo.count_active_comments_by_video_ids(owner_channel_id, video_ids)
    scan_statuses = job_repo.get_latest_scan_statuses(owner_channel_id, video_ids)
    return ok(
        {
            "items": [
                _serialize_video(
                    video,
                    stored_comment_count=stored_counts.get(video.video_id, 0),
                    scan_status=scan_statuses.get(video.video_id, "not_scanned"),
                )
                for video in videos
            ],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "refreshed": sync_mode != "cache",
            "synced_count": synced_count,
            "sync_mode": sync_mode,
            "new_videos": new_videos,
            "updated_videos": updated_videos,
            "metadata_batches": metadata_batches,
            "estimated_quota": estimated_quota,
        }
    )


@bp.get("/<video_id>")
@login_required
def get_video_detail(video_id: str):
    video = video_repo.get_video(g.owner_channel_id, video_id)
    if video is None:
        return fail("video_not_found", "Video tidak ditemukan.", 404)
    stored_counts = comment_repo.count_active_comments_by_video_ids(
        g.owner_channel_id,
        [video.video_id],
    )
    scan_status = job_repo.get_latest_scan_statuses(
        g.owner_channel_id,
        [video.video_id],
    ).get(video.video_id, "not_scanned")
    return ok(
        _serialize_video(
            video,
            stored_comment_count=stored_counts.get(video.video_id, 0),
            scan_status=scan_status,
        )
    )


@bp.post("/<video_id>/scan")
@login_required
def scan_video(video_id: str):
    video = video_repo.get_video(g.owner_channel_id, video_id)
    if video is None:
        return fail("video_not_found", "Video tidak ditemukan.", 404)

    active = job_repo.get_active_scan(g.owner_channel_id, video_id)
    if active is not None:
        return ok(_serialize_job(active), 202)

    job = job_repo.create_job(g.owner_channel_id, video_id)
    submit_scan_job(
        current_app._get_current_object(),
        job.id,
        g.owner_channel_id,
        video_id,
        g.current_user.access_token,
    )
    if current_app.config.get("TESTING"):
        db.session.expire_all()
        job = job_repo.get_job(g.owner_channel_id, job.id) or job
    return ok(_serialize_job(job), 202)
