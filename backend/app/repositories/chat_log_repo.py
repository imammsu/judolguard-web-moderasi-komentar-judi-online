"""Repository riwayat percakapan chatbot dengan filter pemilik."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from ..extensions import db
from ..models import ChatLog


def create_chat_log(
    owner_channel_id: str,
    *,
    session_id: UUID | None = None,
    question: str,
    tool_used: list[str],
    answer: str,
) -> ChatLog:
    log = ChatLog(
        session_id=session_id,
        owner_channel_id=owner_channel_id,
        question=question,
        tool_used=",".join(dict.fromkeys(tool_used)) or None,
        answer=answer,
    )
    try:
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return log


def list_chat_logs(
    owner_channel_id: str,
    limit: int = 50,
    session_id: UUID | None = None,
) -> list[ChatLog]:
    statement = (
        select(ChatLog)
        .where(ChatLog.owner_channel_id == owner_channel_id)
        .order_by(ChatLog.created_at.desc(), ChatLog.id.desc())
        .limit(max(1, min(100, int(limit))))
    )
    if session_id is not None:
        statement = statement.where(ChatLog.session_id == session_id)
    return list(db.session.scalars(statement))


def serialize_chat_log(log: ChatLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "session_id": str(log.session_id) if log.session_id else None,
        "question": log.question,
        "tool_used": log.tool_used.split(",") if log.tool_used else [],
        "answer": log.answer,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
