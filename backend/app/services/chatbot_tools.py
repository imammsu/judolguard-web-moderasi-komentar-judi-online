"""Tool read-only chatbot analisis spam."""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import desc, func, select

from ..extensions import db
from ..models import Comment, Keyword, MonitoredVideo, User, Video
from ..repositories import video_repo

MAX_TOOL_LIMIT = 20


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VideoToolArguments(ToolArguments):
    video_id: str | None = None


class LimitedVideoToolArguments(VideoToolArguments):
    limit: int = Field(default=10, ge=1, le=MAX_TOOL_LIMIT)


class AuthorToolArguments(ToolArguments):
    author: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=10, ge=1, le=MAX_TOOL_LIMIT)


TOOL_DEFINITIONS: list[dict[str, object]] = [
    {
        "name": "top_spammers",
        "description": "Daftar akun berdasarkan jumlah komentar zona judol terbanyak.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "video_id": {"type": "STRING"},
                "limit": {"type": "INTEGER", "minimum": 1, "maximum": MAX_TOOL_LIMIT},
            },
        },
    },
    {
        "name": "count_judol",
        "description": "Jumlah dan persentase komentar judol yang sudah diklasifikasikan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"video_id": {"type": "STRING"}},
        },
    },
    {
        "name": "top_keywords",
        "description": "Keyword atau situs hasil ekstraksi yang paling sering muncul.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "video_id": {"type": "STRING"},
                "limit": {"type": "INTEGER", "minimum": 1, "maximum": MAX_TOOL_LIMIT},
            },
        },
    },
    {
        "name": "comments_by_author",
        "description": "Komentar judol dari akun berdasarkan author_channel_id.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "author": {"type": "STRING"},
                "limit": {"type": "INTEGER", "minimum": 1, "maximum": MAX_TOOL_LIMIT},
            },
            "required": ["author"],
        },
    },
    {
        "name": "peak_hours",
        "description": "Jam publikasi dengan komentar judol terbanyak.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"video_id": {"type": "STRING"}},
        },
    },
    {
        "name": "duplicate_comments",
        "description": "Komentar judol yang muncul berulang dengan teks sama.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "video_id": {"type": "STRING"},
                "limit": {"type": "INTEGER", "minimum": 1, "maximum": MAX_TOOL_LIMIT},
            },
        },
    },
    {
        "name": "compare_videos",
        "description": (
            "Peringkat video milik user berdasarkan jumlah komentar judol tersimpan. "
            "Gunakan untuk pertanyaan video yang paling diserang, paling banyak spam, "
            "paling berisiko, atau perlu diwaspadai."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {"limit": {"type": "INTEGER", "minimum": 1, "maximum": MAX_TOOL_LIMIT}},
        },
    },
]


def _video_filter(owner_channel_id: str, video_id: str | None) -> list[Any]:
    filters: list[Any] = [
        Comment.owner_channel_id == owner_channel_id,
        Comment.zone == "judol",
    ]
    if video_id:
        if video_repo.get_video(owner_channel_id, video_id) is None:
            raise ValueError("Video tidak ditemukan.")
        filters.append(Comment.video_id == video_id)
    return filters


def _limit(value: object) -> int:
    return max(1, min(MAX_TOOL_LIMIT, int(value or 10)))


def top_spammers(
    owner_channel_id: str,
    *,
    video_id: str | None = None,
    limit: int = 10,
) -> dict[str, object]:
    filters = _video_filter(owner_channel_id, video_id)
    filters.append(Comment.author_channel_id.is_not(None))
    statement = (
        select(
            Comment.author_channel_id,
            func.max(Comment.author_name).label("author_name"),
            func.count(Comment.comment_id).label("comment_count"),
        )
        .where(*filters)
        .group_by(Comment.author_channel_id)
        .order_by(desc("comment_count"), Comment.author_channel_id.asc())
        .limit(_limit(limit))
    )
    items = [
        {
            "author_channel_id": row.author_channel_id,
            "author_name": row.author_name,
            "comment_count": int(row.comment_count),
        }
        for row in db.session.execute(statement)
    ]
    return {"video_id": video_id, "items": items, "total": len(items)}


def count_judol(
    owner_channel_id: str,
    *,
    video_id: str | None = None,
) -> dict[str, object]:
    filters: list[Any] = [
        Comment.owner_channel_id == owner_channel_id,
        Comment.classified_at.is_not(None),
    ]
    if video_id:
        if video_repo.get_video(owner_channel_id, video_id) is None:
            raise ValueError("Video tidak ditemukan.")
        filters.append(Comment.video_id == video_id)
    total = int(db.session.scalar(select(func.count()).select_from(Comment).where(*filters)) or 0)
    judol_filters = [*filters, Comment.zone == "judol"]
    judol = int(
        db.session.scalar(select(func.count()).select_from(Comment).where(*judol_filters))
        or 0
    )
    percentage = round(judol / total * 100, 2) if total else 0
    return {
        "video_id": video_id,
        "classified_comments": total,
        "judol_comments": judol,
        "judol_percentage": percentage,
    }


def top_keywords(
    owner_channel_id: str,
    *,
    video_id: str | None = None,
    limit: int = 10,
) -> dict[str, object]:
    filters: list[Any] = [Keyword.owner_channel_id == owner_channel_id]
    if video_id:
        if video_repo.get_video(owner_channel_id, video_id) is None:
            raise ValueError("Video tidak ditemukan.")
        filters.append(Keyword.video_id == video_id)
    statement = (
        select(Keyword.video_id, Keyword.keyword, Keyword.type, Keyword.frequency)
        .where(*filters)
        .order_by(Keyword.frequency.desc(), Keyword.keyword.asc())
        .limit(_limit(limit))
    )
    items = [
        {
            "video_id": row.video_id,
            "keyword": row.keyword,
            "type": row.type,
            "frequency": int(row.frequency),
        }
        for row in db.session.execute(statement)
    ]
    return {"video_id": video_id, "items": items, "total": len(items)}


def comments_by_author(
    owner_channel_id: str,
    *,
    author: str,
    limit: int = 10,
) -> dict[str, object]:
    statement = (
        select(Comment)
        .where(
            Comment.owner_channel_id == owner_channel_id,
            Comment.author_channel_id == author.strip(),
            Comment.zone == "judol",
        )
        .order_by(Comment.published_at.desc().nulls_last(), Comment.comment_id.desc())
        .limit(_limit(limit))
    )
    items = [
        {
            "comment_id": comment.comment_id,
            "video_id": comment.video_id,
            "author_channel_id": comment.author_channel_id,
            "text": comment.text_original,
            "published_at": comment.published_at.isoformat()
            if comment.published_at
            else None,
            "moderation_status": comment.moderation_status,
        }
        for comment in db.session.scalars(statement)
    ]
    return {"author_channel_id": author.strip(), "items": items, "total": len(items)}


def peak_hours(
    owner_channel_id: str,
    *,
    video_id: str | None = None,
) -> dict[str, object]:
    statement = select(Comment.published_at).where(
        *_video_filter(owner_channel_id, video_id),
        Comment.published_at.is_not(None),
    )
    counts: Counter[int] = Counter()
    for published_at in db.session.scalars(statement):
        counts[published_at.hour] += 1
    items = [
        {"hour": hour, "comment_count": count}
        for hour, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {"video_id": video_id, "items": items[:24], "total": sum(counts.values())}


def duplicate_comments(
    owner_channel_id: str,
    *,
    video_id: str | None = None,
    limit: int = 10,
) -> dict[str, object]:
    filters = _video_filter(owner_channel_id, video_id)
    filters.append(Comment.text_original != "")
    statement = (
        select(
            Comment.text_original,
            func.count(Comment.comment_id).label("comment_count"),
        )
        .where(*filters)
        .group_by(Comment.text_original)
        .having(func.count(Comment.comment_id) > 1)
        .order_by(desc("comment_count"), Comment.text_original.asc())
        .limit(_limit(limit))
    )
    items = [
        {"text": row.text_original, "comment_count": int(row.comment_count)}
        for row in db.session.execute(statement)
    ]
    return {"video_id": video_id, "items": items, "total": len(items)}


def compare_videos(owner_channel_id: str, *, limit: int = 10) -> dict[str, object]:
    active_subquery = (
        select(MonitoredVideo.active)
        .join(User, User.id == MonitoredVideo.user_id)
        .where(
            MonitoredVideo.video_id == Video.video_id,
            User.channel_id == owner_channel_id,
        )
        .limit(1)
        .scalar_subquery()
    )
    checked_subquery = (
        select(MonitoredVideo.last_checked_at)
        .join(User, User.id == MonitoredVideo.user_id)
        .where(
            MonitoredVideo.video_id == Video.video_id,
            User.channel_id == owner_channel_id,
        )
        .limit(1)
        .scalar_subquery()
    )
    statement = (
        select(
            Comment.video_id,
            Video.title,
            func.count(Comment.comment_id).label("judol_count"),
            active_subquery.label("monitoring_active"),
            checked_subquery.label("last_checked_at"),
        )
        .join(Video, Video.video_id == Comment.video_id)
        .where(
            Comment.owner_channel_id == owner_channel_id,
            Comment.zone == "judol",
        )
        .group_by(Comment.video_id, Video.title)
        .order_by(desc("judol_count"), Comment.video_id.asc())
        .limit(_limit(limit))
    )
    items = [
        {
            "video_id": row.video_id,
            "title": row.title,
            "judol_count": int(row.judol_count),
            "monitoring_active": bool(row.monitoring_active),
            "last_checked_at": (
                row.last_checked_at.isoformat() if row.last_checked_at else None
            ),
        }
        for row in db.session.execute(statement)
    ]
    return {"items": items, "total": len(items)}


TOOL_HANDLERS = {
    "top_spammers": (LimitedVideoToolArguments, top_spammers),
    "count_judol": (VideoToolArguments, count_judol),
    "top_keywords": (LimitedVideoToolArguments, top_keywords),
    "comments_by_author": (AuthorToolArguments, comments_by_author),
    "peak_hours": (VideoToolArguments, peak_hours),
    "duplicate_comments": (LimitedVideoToolArguments, duplicate_comments),
    "compare_videos": (LimitedVideoToolArguments, compare_videos),
}


def execute_tool(
    owner_channel_id: str,
    name: str,
    arguments: dict[str, object],
) -> dict[str, object]:
    handler_entry = TOOL_HANDLERS.get(name)
    if handler_entry is None:
        raise ValueError("Tool tidak diizinkan.")
    schema, handler = handler_entry
    try:
        parsed = schema.model_validate(arguments)
    except ValidationError as exc:
        raise ValueError("Parameter tool tidak valid.") from exc
    return handler(owner_channel_id, **parsed.model_dump(exclude_none=True))
