"""Repository pairing Telegram dengan filter user database."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from ..extensions import db
from ..models import TelegramLink, User


def get_link_by_user_id(user_id: int) -> TelegramLink | None:
    return db.session.scalars(
        select(TelegramLink).where(TelegramLink.user_id == user_id)
    ).first()


def get_link_by_chat_id(chat_id: int) -> TelegramLink | None:
    return db.session.scalars(
        select(TelegramLink).where(TelegramLink.chat_id == chat_id)
    ).first()


def get_owner_by_chat_id(chat_id: int) -> tuple[User, TelegramLink] | None:
    """Ambil user dan link yang hanya dimiliki chat Telegram tersebut."""
    statement = (
        select(User, TelegramLink)
        .join(TelegramLink, TelegramLink.user_id == User.id)
        .where(TelegramLink.chat_id == chat_id)
    )
    return db.session.execute(statement).first()


def set_paused_by_chat_id(chat_id: int, paused: bool) -> bool:
    link = get_link_by_chat_id(chat_id)
    if link is None:
        return False
    link.paused = paused
    link.updated_at = datetime.now(UTC)
    db.session.commit()
    return True


def unlink_by_chat_id(chat_id: int) -> bool:
    link = get_link_by_chat_id(chat_id)
    if link is None:
        return False
    db.session.delete(link)
    db.session.commit()
    return True


def list_active_users() -> list[User]:
    """Ambil user yang Telegram-nya terhubung dan tidak sedang dijeda."""
    statement = (
        select(User)
        .join(TelegramLink, TelegramLink.user_id == User.id)
        .where(TelegramLink.paused.is_(False))
        .order_by(User.id.asc())
    )
    return list(db.session.scalars(statement))


def pause_link(user_id: int) -> bool:
    """Jeda link Telegram aktif milik user."""
    link = get_link_by_user_id(user_id)
    if link is None:
        return False
    link.paused = True
    link.updated_at = datetime.now(UTC)
    db.session.commit()
    return True


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
