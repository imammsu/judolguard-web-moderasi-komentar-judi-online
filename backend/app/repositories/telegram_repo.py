"""Repository pairing Telegram dengan filter user database."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from ..extensions import db
from ..models import TelegramLink


def get_link_by_user_id(user_id: int) -> TelegramLink | None:
    return db.session.scalars(
        select(TelegramLink).where(TelegramLink.user_id == user_id)
    ).first()


def get_link_by_chat_id(chat_id: int) -> TelegramLink | None:
    return db.session.scalars(
        select(TelegramLink).where(TelegramLink.chat_id == chat_id)
    ).first()


def save_link(user_id: int, chat_id: int) -> TelegramLink:
    link = get_link_by_user_id(user_id)
    now = datetime.now(UTC)
    if link is None:
        link = TelegramLink(
            user_id=user_id,
            chat_id=chat_id,
            paused=False,
            created_at=now,
            updated_at=now,
        )
        db.session.add(link)
    else:
        link.chat_id = chat_id
        link.paused = False
        link.updated_at = now
    return link
