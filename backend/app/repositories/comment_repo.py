"""Repository komentar: fetch cache, klasifikasi, filter, dan pagination."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..extensions import db
from ..models import Comment


def get_comment_ids(owner_channel_id: str, video_id: str) -> set[str]:
    stmt = select(Comment.comment_id).where(
        Comment.owner_channel_id == owner_channel_id,
        Comment.video_id == video_id,
    )
    return set(db.session.scalars(stmt))


def get_unclassified_comments(owner_channel_id: str, video_id: str) -> list[Comment]:
    stmt = (
        select(Comment)
        .where(
            Comment.owner_channel_id == owner_channel_id,
            Comment.video_id == video_id,
            Comment.zone.is_(None),
        )
        .order_by(Comment.published_at.asc(), Comment.comment_id.asc())
    )
    return list(db.session.scalars(stmt))


def mark_comments_notified(owner_channel_id: str, comment_ids: list[str]) -> int:
    """Tandai komentar alert setelah pesan Telegram berhasil dikirim."""
    if not comment_ids:
        return 0
    statement = (
        update(Comment)
        .where(
            Comment.owner_channel_id == owner_channel_id,
            Comment.comment_id.in_(comment_ids),
            Comment.zone.in_(("judol", "review")),
            Comment.notified.is_(False),
        )
        .values(notified=True, notified_at=datetime.now(UTC))
    )
    try:
        updated = int(db.session.execute(statement).rowcount or 0)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return updated


def get_owned_comments_by_ids(owner_channel_id: str, comment_ids: list[str]) -> list[Comment]:
    if not comment_ids:
        return []
    stmt = select(Comment).where(
        Comment.owner_channel_id == owner_channel_id,
        Comment.comment_id.in_(comment_ids),
    )
    return list(db.session.scalars(stmt))


def get_judol_comments(owner_channel_id: str, video_id: str | None = None) -> list[Comment]:
    filters = [
        Comment.owner_channel_id == owner_channel_id,
        Comment.zone == "judol",
        Comment.moderation_status != "rejected",
    ]
    if video_id:
        filters.append(Comment.video_id == video_id)
    stmt = select(Comment).where(*filters).order_by(Comment.score.desc().nulls_last())
    return list(db.session.scalars(stmt))


def count_today_judol(owner_channel_id: str, start_at: datetime) -> int:
    statement = select(func.count(Comment.comment_id)).where(
        Comment.owner_channel_id == owner_channel_id,
        Comment.zone == "judol",
        Comment.moderation_status != "rejected",
        Comment.published_at >= start_at,
    )
    return int(db.session.scalar(statement) or 0)


def get_video_stats(owner_channel_id: str) -> list[dict[str, Any]]:
    """Ringkasan komentar per video milik channel tertentu."""
    judol_count = func.sum(case((Comment.zone == "judol", 1), else_=0))
    review_count = func.sum(case((Comment.zone == "review", 1), else_=0))
    normal_count = func.sum(case((Comment.zone == "bukan", 1), else_=0))
    statement = (
        select(
            Comment.video_id,
            judol_count.label("judol_count"),
            review_count.label("review_count"),
            normal_count.label("normal_count"),
        )
        .where(
            Comment.owner_channel_id == owner_channel_id,
            Comment.moderation_status != "rejected",
        )
        .group_by(Comment.video_id)
        .order_by(judol_count.desc(), Comment.video_id.asc())
    )
    return [
        {
            "video_id": video_id,
            "judol_count": int(judol or 0),
            "review_count": int(review or 0),
            "normal_count": int(normal or 0),
        }
        for video_id, judol, review, normal in db.session.execute(statement)
    ]


def get_top_spammers(owner_channel_id: str, limit: int = 10) -> list[dict[str, Any]]:
    spammer_key = func.coalesce(Comment.author_channel_id, Comment.author_name)
    statement = (
        select(
            spammer_key.label("spammer_key"),
            func.max(Comment.author_name).label("author_name"),
            func.count(Comment.comment_id).label("comment_count"),
        )
        .where(
            Comment.owner_channel_id == owner_channel_id,
            Comment.zone == "judol",
            Comment.moderation_status != "rejected",
        )
        .group_by(spammer_key)
        .order_by(func.count(Comment.comment_id).desc())
        .limit(max(1, int(limit)))
    )
    return [
        {
            "author_channel_id": spammer_key,
            "author_name": author_name or "Akun tanpa nama",
            "comment_count": int(comment_count),
        }
        for spammer_key, author_name, comment_count in db.session.execute(statement)
    ]


def get_extractable_judol_comments(owner_channel_id: str, video_id: str) -> list[Comment]:
    """Ambil semua komentar judol terklasifikasi, termasuk yang sudah direject."""
    statement = (
        select(Comment)
        .where(
            Comment.owner_channel_id == owner_channel_id,
            Comment.video_id == video_id,
            Comment.zone == "judol",
            Comment.classified_at.is_not(None),
            Comment.text_original != "",
        )
        .order_by(Comment.published_at.asc().nulls_last(), Comment.comment_id.asc())
    )
    return list(db.session.scalars(statement))


def count_active_comments_by_video_ids(
    owner_channel_id: str,
    video_ids: list[str] | set[str],
) -> dict[str, int]:
    """Hitung komentar lokal yang belum direject untuk banyak video sekaligus."""
    clean_ids = list(dict.fromkeys(str(video_id) for video_id in video_ids if video_id))
    if not clean_ids:
        return {}

    statement = (
        select(Comment.video_id, func.count(Comment.comment_id))
        .where(
            Comment.owner_channel_id == owner_channel_id,
            Comment.video_id.in_(clean_ids),
            Comment.moderation_status != "rejected",
        )
        .group_by(Comment.video_id)
    )
    return {
        str(video_id): int(count)
        for video_id, count in db.session.execute(statement)
    }


def mark_moderation_status(owner_channel_id: str, comment_ids: list[str], status: str) -> int:
    if not comment_ids:
        return 0
    statement = (
        update(Comment)
        .where(
            Comment.owner_channel_id == owner_channel_id,
            Comment.comment_id.in_(comment_ids),
        )
        .values(moderation_status=status)
    )
    try:
        updated = int(db.session.execute(statement).rowcount or 0)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return updated


def bulk_upsert_comments(
    owner_channel_id: str,
    video_id: str,
    comments: list[dict[str, Any]],
) -> int:
    if not comments:
        return 0

    comment_ids = [str(comment["comment_id"]) for comment in comments if comment.get("comment_id")]
    existing_rows = db.session.execute(
        select(Comment.comment_id, Comment.text_original).where(
            Comment.owner_channel_id == owner_channel_id,
            Comment.video_id == video_id,
            Comment.comment_id.in_(comment_ids),
        )
    )
    existing_text = {row.comment_id: row.text_original for row in existing_rows}

    rows = [
        {
            "comment_id": str(comment["comment_id"]),
            "video_id": video_id,
            "owner_channel_id": owner_channel_id,
            "author_name": comment.get("author_name"),
            "author_channel_id": comment.get("author_channel_id"),
            "text_original": str(comment.get("text_original") or ""),
            "published_at": comment.get("published_at"),
            "like_count": int(comment.get("like_count") or 0),
            "rule_hit": False,
            "moderation_status": "none",
        }
        for comment in comments
        if comment.get("comment_id")
    ]
    if not rows:
        return 0

    bind = db.session.get_bind()
    insert = postgres_insert if bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(Comment.__table__).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=["comment_id"],
        set_={
            "video_id": statement.excluded.video_id,
            "owner_channel_id": statement.excluded.owner_channel_id,
            "author_name": statement.excluded.author_name,
            "author_channel_id": statement.excluded.author_channel_id,
            "text_original": statement.excluded.text_original,
            "published_at": statement.excluded.published_at,
            "like_count": statement.excluded.like_count,
        },
    )
    db.session.execute(statement)

    changed_ids = [
        row["comment_id"]
        for row in rows
        if row["comment_id"] in existing_text
        and existing_text[row["comment_id"]] != row["text_original"]
    ]
    if changed_ids:
        db.session.execute(
            update(Comment)
            .where(
                Comment.owner_channel_id == owner_channel_id,
                Comment.video_id == video_id,
                Comment.comment_id.in_(changed_ids),
            )
            .values(
                text_prepared=None,
                text_hash=None,
                zone=None,
                score=None,
                rule_hit=False,
                model_version=None,
                classified_at=None,
                user_label=None,
            )
        )

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return len(rows)


def bulk_update_classifications(
    owner_channel_id: str,
    video_id: str,
    classifications: list[dict[str, Any]],
) -> int:
    if not classifications:
        return 0

    classified_at = datetime.now(UTC)
    updated = 0
    for result in classifications:
        statement = (
            update(Comment)
            .where(
                Comment.comment_id == result["comment_id"],
                Comment.owner_channel_id == owner_channel_id,
                Comment.video_id == video_id,
            )
            .values(
                text_prepared=result["text_prepared"],
                text_hash=result["text_hash"],
                zone=result["zone"],
                score=result["score"],
                rule_hit=bool(result["rule_hit"]),
                model_version=result["model_version"],
                classified_at=classified_at,
            )
        )
        updated += int(db.session.execute(statement).rowcount or 0)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return updated


def list_comments(
    owner_channel_id: str,
    video_id: str,
    *,
    zone: str | None,
    search: str | None,
    sort: str,
    page: int,
    page_size: int,
    moderation_status: str = "active",
) -> tuple[list[Comment], int]:
    filters = [
        Comment.owner_channel_id == owner_channel_id,
        Comment.video_id == video_id,
    ]
    if zone in {"judol", "review", "bukan"}:
        filters.append(Comment.zone == zone)
    if search:
        filters.append(Comment.text_original.ilike(f"%{search}%"))
    if moderation_status == "active":
        filters.append(Comment.moderation_status != "rejected")
    elif moderation_status == "rejected":
        filters.append(Comment.moderation_status == "rejected")

    total = int(
        db.session.scalar(
            select(func.count()).select_from(Comment).where(*filters)
        )
        or 0
    )
    order_column = {
        "score_asc": Comment.score.asc().nulls_last(),
        "newest": Comment.published_at.desc().nulls_last(),
        "oldest": Comment.published_at.asc().nulls_last(),
    }.get(sort, Comment.score.desc().nulls_last())
    stmt = (
        select(Comment)
        .where(*filters)
        .order_by(order_column, Comment.comment_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.session.scalars(stmt)), total
