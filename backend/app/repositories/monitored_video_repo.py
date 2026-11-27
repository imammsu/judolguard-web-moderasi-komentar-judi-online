"""Repository video yang dipantau Sentinel."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

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


def list_active_monitored_videos(user_id: int) -> list[MonitoredVideo]:
    statement = (
        select(MonitoredVideo)
        .where(
            MonitoredVideo.user_id == user_id,
            MonitoredVideo.active.is_(True),
        )
        .order_by(MonitoredVideo.created_at.asc(), MonitoredVideo.video_id.asc())
    )
    return list(db.session.scalars(statement))


def set_monitoring(
    user_id: int,
    video_id: str,
    *,
    active: bool,
    reset_baseline: bool = False,
) -> MonitoredVideo:
    monitored = get_monitored_video(user_id, video_id)
    if monitored is None:
        monitored = MonitoredVideo(
            user_id=user_id,
            video_id=video_id,
            last_comment_count=None,
            active=active,
        )
        db.session.add(monitored)
    else:
        monitored.active = active
        if reset_baseline:
            monitored.last_comment_count = None
            monitored.last_checked_at = None

    db.session.commit()
    return monitored


def deactivate_all() -> int:
    """Nonaktifkan target monitoring lama saat mode monitoring menjadi opt-in."""
    statement = select(MonitoredVideo).where(MonitoredVideo.active.is_(True))
    rows = list(db.session.scalars(statement))
    for row in rows:
        row.active = False
    if rows:
        db.session.commit()
    return len(rows)


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


def get_user_monitor_summary(user_id: int) -> tuple[int, datetime | None]:
    statement = select(
        func.count(MonitoredVideo.id),
        func.max(MonitoredVideo.last_checked_at),
    ).where(
        MonitoredVideo.user_id == user_id,
        MonitoredVideo.active.is_(True),
    )
    count, last_checked_at = db.session.execute(statement).one()
    return int(count or 0), last_checked_at
