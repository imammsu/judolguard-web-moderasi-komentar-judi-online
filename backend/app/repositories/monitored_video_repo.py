"""Repository video yang dipantau Sentinel."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from ..extensions import db
from ..models import MonitoredVideo


def get_monitored_video(user_id: int, video_id: str) -> MonitoredVideo | None:
    statement = select(MonitoredVideo).where(
        MonitoredVideo.user_id == user_id,
        MonitoredVideo.video_id == video_id,
    )
    return db.session.scalars(statement).first()


def get_or_create_monitored_video(user_id: int, video_id: str) -> MonitoredVideo:
    monitored = get_monitored_video(user_id, video_id)
    if monitored is not None:
        return monitored

    monitored = MonitoredVideo(
        user_id=user_id,
        video_id=video_id,
        last_comment_count=None,
        active=True,
    )
    db.session.add(monitored)
    db.session.flush()
    return monitored


def update_baseline(
    monitored: MonitoredVideo,
    comment_count: int,
    *,
    checked_at: datetime | None = None,
) -> None:
    monitored.last_comment_count = max(0, int(comment_count))
    monitored.last_checked_at = checked_at or datetime.now(UTC)


def mark_checked(
    monitored: MonitoredVideo,
    *,
    checked_at: datetime | None = None,
) -> None:
    monitored.last_checked_at = checked_at or datetime.now(UTC)
