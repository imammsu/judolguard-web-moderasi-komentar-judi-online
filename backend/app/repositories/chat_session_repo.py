"""Repository sesi chatbot dengan validasi kepemilikan channel."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from ..extensions import db
from ..models import ChatSession, Video


def create_session(owner_channel_id: str, video_id: str | None = None) -> ChatSession:
    title = "Analisis seluruh channel"
    if video_id:
        video = db.session.scalars(
            select(Video).where(
                Video.video_id == video_id,
                Video.owner_channel_id == owner_channel_id,
            )
        ).first()
        if video is None:
            raise ValueError("Video tidak ditemukan atau bukan milik channel Anda.")
        title = f"Analisis video: {video.title or video.video_id}"

    session = ChatSession(
        owner_channel_id=owner_channel_id,
        video_id=video_id,
        title=title,
    )
    try:
        db.session.add(session)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return session


def get_session(owner_channel_id: str, session_id: UUID) -> ChatSession | None:
    statement = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.owner_channel_id == owner_channel_id,
    )
    return db.session.scalars(statement).first()


def list_sessions(
    owner_channel_id: str,
    video_id: str | None = None,
    limit: int = 50,
) -> list[ChatSession]:
    statement = select(ChatSession).where(
        ChatSession.owner_channel_id == owner_channel_id
    )
    if video_id is not None:
        statement = statement.where(ChatSession.video_id == video_id)
    statement = statement.order_by(
        ChatSession.updated_at.desc(),
        ChatSession.created_at.desc(),
    ).limit(max(1, min(100, int(limit))))
    return list(db.session.scalars(statement))


def touch_session(session: ChatSession) -> None:
    session.updated_at = datetime.now(UTC)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def delete_session(owner_channel_id: str, session_id: UUID) -> bool:
    session = get_session(owner_channel_id, session_id)
    if session is None:
        return False
    try:
        db.session.delete(session)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return True


def serialize_session(session: ChatSession) -> dict[str, Any]:
    return {
        "id": str(session.id),
        "video_id": session.video_id,
        "title": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }
