"""Siklus patroli Sentinel: baseline commentCount dan komentar incremental."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from math import ceil
from typing import Any

from flask import Flask

from ..models import User
from ..repositories import (
    comment_repo,
    monitored_video_repo,
    patrol_repo,
    telegram_repo,
    video_repo,
)
from ..services import comment_classifier, google_token, telegram_notifications, youtube
from ..services.google_token import (
    GoogleTokenError,
    InvalidGrantError,
    MissingRefreshTokenError,
)

logger = logging.getLogger(__name__)

_PATROL_LOCK = threading.Lock()


@dataclass
class PatrolUserSummary:
    user_id: int
    videos_checked: int = 0
    est_api_units: int = 0
    new_comments: int = 0
    classified_comments: int = 0
    error: str | None = None
    patrol_run_id: int | None = None
    notification_plans: list[telegram_notifications.NotificationPlan] = field(
        default_factory=list
    )


@dataclass
class PatrolCycleSummary:
    users_checked: int = 0
    videos_checked: int = 0
    new_comments: int = 0
    classified_comments: int = 0
    errors: list[str] = field(default_factory=list)
    notification_plans: list[telegram_notifications.NotificationPlan] = field(
        default_factory=list
    )
    skipped_locked: bool = False


def _error_text(error: Exception) -> str:
    if isinstance(error, (GoogleTokenError, youtube.YouTubeServiceError)):
        return f"{error.code}: {error.message}"
    return f"{type(error).__name__}: proses patroli gagal."


def _video_api_units(video_count: int) -> int:
    """Estimasi videos.list untuk target monitoring dalam batch maksimal 50 ID."""
    if video_count <= 0:
        return 0
    return ceil(video_count / youtube.VIDEO_BATCH_SIZE)


def _append_error(summary: PatrolUserSummary, message: str) -> None:
    summary.error = f"{summary.error}; {message}" if summary.error else message


def _classify_pending(
    *,
    app: Flask,
    user: User,
    video_id: str,
    summary: PatrolUserSummary,
) -> None:
    try:
        summary.classified_comments += comment_classifier.classify_pending_comments(
            user.channel_id,
            video_id,
            batch_size=int(app.config.get("SENTINEL_CLASSIFICATION_BATCH_SIZE", 100)),
            max_comments=int(
                app.config.get("SENTINEL_MAX_CLASSIFICATIONS_PER_CYCLE", 500)
            ),
        )
    except Exception as error:  # noqa: BLE001
        from ..extensions import db

        db.session.rollback()
        _append_error(summary, f"{video_id}: klasifikasi gagal ({type(error).__name__})")
        logger.exception(
            "Klasifikasi komentar gagal; user_id=%s video_id=%s",
            user.id,
            video_id,
        )


def _commit_monitor_change() -> None:
    try:
        from ..extensions import db

        db.session.commit()
    except Exception:
        from ..extensions import db

        db.session.rollback()
        raise


def _process_video(
    *,
    app: Flask,
    user: User,
    video: dict[str, Any],
    access_token: str,
    summary: PatrolUserSummary,
) -> None:
    video_id = str(video.get("video_id") or "")
    if not video_id:
        return

    existing_video = video_repo.get_video_by_id(video_id)
    if existing_video is not None and existing_video.owner_channel_id != user.channel_id:
        summary.error = (
            f"{summary.error}; video {video_id} bukan milik channel user"
            if summary.error
            else f"video {video_id} bukan milik channel user"
        )
        return

    comment_count = video.get("comment_count")
    if comment_count is None:
        summary.error = (
            f"{summary.error}; commentCount tidak tersedia untuk video {video_id}"
            if summary.error
            else f"commentCount tidak tersedia untuk video {video_id}"
        )
        return

    monitored = monitored_video_repo.get_monitored_video(user.id, video_id)
    if monitored is None or not monitored.active:
        return
    current_count = max(0, int(comment_count))

    if monitored.last_comment_count is None:
        monitored_video_repo.update_baseline(monitored, current_count)
        _commit_monitor_change()
        _classify_pending(app=app, user=user, video_id=video_id, summary=summary)
        return

    if monitored.last_comment_count == current_count:
        monitored_video_repo.mark_checked(monitored)
        _commit_monitor_change()
        _classify_pending(app=app, user=user, video_id=video_id, summary=summary)
        return

    known_comment_ids = comment_repo.get_comment_ids(user.channel_id, video_id)
    try:
        fetched = youtube.fetch_video_comments(
            access_token=access_token,
            video_id=video_id,
            known_comment_ids=known_comment_ids,
            max_comments=int(app.config.get("MAX_COMMENTS_PER_SCAN", 2000)),
            max_pages=int(app.config.get("MAX_COMMENT_PAGES_PER_SCAN", 20)),
        )
    except youtube.YouTubeServiceError as error:
        if error.code == "comments_disabled":
            monitored_video_repo.update_baseline(monitored, current_count)
            _commit_monitor_change()
            _append_error(summary, f"{video_id}: comments_disabled")
            _classify_pending(app=app, user=user, video_id=video_id, summary=summary)
            return
        raise

    if fetched.comments:
        summary.new_comments += comment_repo.bulk_upsert_comments(
            user.channel_id,
            video_id,
            fetched.comments,
        )
    summary.est_api_units += fetched.pages_fetched
    monitored_video_repo.update_baseline(monitored, current_count)
    _commit_monitor_change()
    _classify_pending(app=app, user=user, video_id=video_id, summary=summary)


def _process_user(app: Flask, user: User) -> PatrolUserSummary:
    summary = PatrolUserSummary(user_id=user.id)
    try:
        access_token = google_token.refresh_access_token(app, user.id).access_token
    except (MissingRefreshTokenError, InvalidGrantError) as error:
        telegram_repo.pause_link(user.id)
        summary.error = _error_text(error)
        run = patrol_repo.create_patrol_run(
            user.id,
            est_api_units=0,
            error=summary.error,
        )
        summary.patrol_run_id = run.id
        return summary
    except GoogleTokenError as error:
        summary.error = _error_text(error)
        run = patrol_repo.create_patrol_run(user.id, error=summary.error)
        summary.patrol_run_id = run.id
        return summary

    valid_video_ids: list[str] = []
    try:
        monitored_rows = monitored_video_repo.list_active_monitored_videos(user.id)
        max_monitored = max(
            0,
            int(app.config.get("SENTINEL_MAX_MONITORED_VIDEOS", 50)),
        )
        monitored_rows = monitored_rows[:max_monitored]
        monitored_video_ids = [row.video_id for row in monitored_rows]
        summary.est_api_units = _video_api_units(len(monitored_video_ids))
        if not monitored_video_ids:
            run = patrol_repo.create_patrol_run(
                user.id,
                videos_checked=0,
                est_api_units=0,
                error=None,
            )
            summary.patrol_run_id = run.id
            return summary

        videos = youtube.fetch_video_metadata(
            access_token,
            monitored_video_ids,
        )
        summary.videos_checked = len(videos)

        valid_videos = []
        for video in videos:
            existing_video = video_repo.get_video_by_id(str(video.get("video_id") or ""))
            if existing_video is None or existing_video.owner_channel_id == user.channel_id:
                valid_videos.append(video)
        if valid_videos:
            video_repo.bulk_upsert_videos(user.channel_id, valid_videos)
            valid_video_ids = [
                str(video["video_id"])
                for video in valid_videos
                if video.get("video_id")
            ]

        for video in videos:
            try:
                _process_video(
                    app=app,
                    user=user,
                    video=video,
                    access_token=access_token,
                    summary=summary,
                )
            except Exception as error:  # noqa: BLE001
                from ..extensions import db

                db.session.rollback()
                text = _error_text(error)
                _append_error(summary, f"{video.get('video_id')}: {text}")
                logger.exception(
                    "Patroli video gagal; user_id=%s video_id=%s",
                    user.id,
                    video.get("video_id"),
                )
    except Exception as error:  # noqa: BLE001
        summary.error = _error_text(error)
        logger.exception("Patroli user gagal; user_id=%s", user.id)

    run = patrol_repo.create_patrol_run(
        user.id,
        videos_checked=summary.videos_checked,
        est_api_units=summary.est_api_units,
        new_comments=summary.new_comments,
        error=summary.error,
    )
    summary.patrol_run_id = run.id
    try:
        summary.notification_plans = telegram_notifications.build_notification_plans(
            user_id=user.id,
            owner_channel_id=user.channel_id,
            patrol_run_id=run.id,
            video_ids=valid_video_ids,
            web_base_url=str(app.config.get("TELEGRAM_WEB_BASE_URL") or ""),
            default_min_alert_count=int(
                app.config.get("SENTINEL_MIN_ALERT_COUNT", 1)
            ),
        )
    except Exception as error:  # noqa: BLE001
        _append_error(summary, f"notifikasi gagal disiapkan ({type(error).__name__})")
        logger.exception("Plan notifikasi gagal dibuat; user_id=%s", user.id)
        patrol_repo.record_notification_delivery(
            run.id,
            alerts_sent=0,
            error=f"Plan notifikasi gagal dibuat ({type(error).__name__}).",
        )
    return summary


def run_patrol_cycle(app: Flask) -> PatrolCycleSummary:
    """Jalankan satu siklus tanpa mengizinkan siklus overlap dalam satu worker."""
    if not _PATROL_LOCK.acquire(blocking=False):
        return PatrolCycleSummary(skipped_locked=True)

    result = PatrolCycleSummary()
    try:
        with app.app_context():
            users = telegram_repo.list_active_users()
            for user in users:
                result.users_checked += 1
                try:
                    user_summary = _process_user(app, user)
                except Exception as error:  # noqa: BLE001
                    user_summary = PatrolUserSummary(
                        user_id=user.id,
                        error=_error_text(error),
                    )
                    patrol_repo.create_patrol_run(user.id, error=user_summary.error)
                    logger.exception("Patroli user tidak terduga gagal; user_id=%s", user.id)

                result.videos_checked += user_summary.videos_checked
                result.new_comments += user_summary.new_comments
                result.classified_comments += user_summary.classified_comments
                result.notification_plans.extend(user_summary.notification_plans)
                if user_summary.error:
                    result.errors.append(f"user_id={user.id}: {user_summary.error}")
    finally:
        _PATROL_LOCK.release()

    return result
