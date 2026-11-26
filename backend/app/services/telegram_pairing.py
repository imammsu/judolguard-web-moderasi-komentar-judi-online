"""Pembuatan dan konsumsi token pairing Telegram sekali pakai."""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from ..extensions import db
from ..models import PairingToken
from ..repositories import telegram_repo

BOT_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{5,32}bot$", re.IGNORECASE)


class PairingError(Exception):
    """Error aman untuk ditampilkan pada bot atau API pairing."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PairingLink:
    url: str
    expires_at: datetime
    expires_in: int


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _clean_bot_username(username: str) -> str:
    cleaned = username.strip().lstrip("@")
    if not BOT_USERNAME_PATTERN.fullmatch(cleaned):
        raise PairingError(
            "telegram_bot_not_configured",
            "TELEGRAM_BOT_USERNAME belum dikonfigurasi dengan benar.",
        )
    return cleaned


def create_pairing_link(
    user_id: int,
    bot_username: str,
    ttl_seconds: int,
) -> PairingLink:
    username = _clean_bot_username(bot_username)
    ttl = max(60, min(3600, int(ttl_seconds)))
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl)

    try:
        db.session.execute(
            delete(PairingToken).where(
                PairingToken.user_id == user_id,
                PairingToken.used_at.is_(None),
            )
        )
        db.session.add(
            PairingToken(
                token_hash=_hash_token(raw_token),
                user_id=user_id,
                expires_at=expires_at,
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return PairingLink(
        url=f"https://t.me/{username}?start={raw_token}",
        expires_at=expires_at,
        expires_in=ttl,
    )


def consume_pairing_token(raw_token: str, chat_id: int) -> int:
    """Konsumsi token secara atomic dan kembalikan user_id pemiliknya."""
    if not raw_token or not chat_id:
        raise PairingError("invalid_pairing_token", "Token pairing tidak valid.")

    token_hash = _hash_token(raw_token)
    statement = select(PairingToken).where(PairingToken.token_hash == token_hash)
    bind = db.session.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        statement = statement.with_for_update()
    token = db.session.scalars(statement).first()
    now = datetime.now(UTC)

    if (
        token is None
        or token.used_at is not None
        or _as_utc(token.expires_at) <= now
    ):
        raise PairingError(
            "invalid_pairing_token",
            "Token pairing tidak valid, sudah digunakan, atau sudah kedaluwarsa.",
        )

    existing_chat = telegram_repo.get_link_by_chat_id(chat_id)
    if existing_chat is not None and existing_chat.user_id != token.user_id:
        raise PairingError(
            "telegram_already_linked",
            "Akun Telegram ini sudah terhubung ke akun JudolGuard lain.",
        )

    try:
        link = telegram_repo.save_link(token.user_id, chat_id)
        token.used_at = now
        link.updated_at = now
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return token.user_id


def mask_chat_id(chat_id: int) -> str:
    value = str(chat_id)
    return f"****{value[-4:]}" if len(value) > 4 else "****"
