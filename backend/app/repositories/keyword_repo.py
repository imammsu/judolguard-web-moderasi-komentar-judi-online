"""Repository hasil ekstraksi keyword per video."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select

from ..extensions import db
from ..models import Keyword


def list_keywords(owner_channel_id: str, video_id: str) -> list[Keyword]:
    statement = (
        select(Keyword)
        .where(
            Keyword.owner_channel_id == owner_channel_id,
            Keyword.video_id == video_id,
        )
        .order_by(Keyword.frequency.desc(), Keyword.keyword.asc())
    )
    return list(db.session.scalars(statement))


def replace_keywords(
    owner_channel_id: str,
    video_id: str,
    keywords: list[dict[str, Any]],
) -> int:
    """Ganti hasil lama hanya setelah ekstraksi seluruhnya berhasil."""
    try:
        db.session.execute(
            delete(Keyword).where(
                Keyword.owner_channel_id == owner_channel_id,
                Keyword.video_id == video_id,
            )
        )
        db.session.add_all(
            [
                Keyword(
                    owner_channel_id=owner_channel_id,
                    video_id=video_id,
                    keyword=str(item["keyword"]),
                    type=str(item["type"]),
                    frequency=max(1, int(item["frequency"])),
                    extracted_at=datetime.now(UTC),
                )
                for item in keywords
            ]
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return len(keywords)
