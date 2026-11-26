"""Repository query dan bulk upsert untuk cache video channel."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..extensions import db
from ..models import Video


def get_latest_fetched_at(owner_channel_id: str) -> datetime | None:
    stmt = select(func.max(Video.last_fetched_at)).where(Video.owner_channel_id == owner_channel_id)
    return db.session.scalar(stmt)


def count_videos(owner_channel_id: str) -> int:
    stmt = select(func.count()).select_from(Video).where(Video.owner_channel_id == owner_channel_id)
    return int(db.session.scalar(stmt) or 0)


def get_video_ids(owner_channel_id: str) -> set[str]:
    stmt = select(Video.video_id).where(Video.owner_channel_id == owner_channel_id)
    return set(db.session.scalars(stmt))


def get_video(owner_channel_id: str, video_id: str) -> Video | None:
    stmt = select(Video).where(
        Video.owner_channel_id == owner_channel_id,
        Video.video_id == video_id,
    )
    return db.session.scalars(stmt).first()


def get_video_by_id(video_id: str) -> Video | None:
    if not video_id:
        return None
    return db.session.get(Video, video_id)


def list_videos(owner_channel_id: str, page: int, page_size: int) -> list[Video]:
    stmt = (
        select(Video)
        .where(Video.owner_channel_id == owner_channel_id)
        .order_by(Video.published_at.desc(), Video.video_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.session.scalars(stmt))


def bulk_upsert_videos(
    owner_channel_id: str,
    videos: list[dict[str, Any]],
    fetched_at: datetime | None = None,
) -> int:
    if not videos:
        return 0

    fetched_at = fetched_at or datetime.now(UTC)
    candidate_rows = [
        {
            "video_id": str(video["video_id"]),
            "owner_channel_id": owner_channel_id,
            "title": video.get("title"),
            "thumbnail_url": video.get("thumbnail_url"),
            "published_at": video.get("published_at"),
            "comment_count": (
                int(video["comment_count"])
                if video.get("comment_count") is not None
                else None
            ),
            "last_fetched_at": fetched_at,
        }
        for video in videos
        if video.get("video_id")
    ]
    if not candidate_rows:
        return 0

    video_ids = [row["video_id"] for row in candidate_rows]
    existing_counts = {
        video_id: int(comment_count)
        for video_id, comment_count in db.session.execute(
            select(Video.video_id, Video.comment_count).where(Video.video_id.in_(video_ids))
        )
    }
    rows = [
        {
            **row,
            "comment_count": (
                row["comment_count"]
                if row["comment_count"] is not None
                else existing_counts.get(row["video_id"], 0)
            ),
        }
        for row in candidate_rows
    ]

    bind = db.session.get_bind()
    insert = postgres_insert if bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(Video.__table__).values(rows)
    update_columns = {
        column: getattr(statement.excluded, column)
        for column in (
            "owner_channel_id",
            "title",
            "thumbnail_url",
            "published_at",
            "comment_count",
            "last_fetched_at",
        )
    }
    statement = statement.on_conflict_do_update(
        index_elements=["video_id"],
        set_=update_columns,
    )
    try:
        result = db.session.execute(statement)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return int(result.rowcount or 0)
