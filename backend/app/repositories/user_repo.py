"""Repository untuk tabel `users` (PRD Part 3 & 14.1).

Setiap operasi membaca/menulis pengguna difilter berdasarkan ``channel_id``
dan ``refresh_token`` selalu disimpan terenkripsi dengan Fernet.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from ..extensions import db
from ..models import User
from ..services.crypto import decrypt_token, encrypt_token


def get_user_by_channel_id(channel_id: str) -> User | None:
    if not channel_id:
        return None
    stmt = select(User).where(User.channel_id == channel_id)
    return db.session.scalars(stmt).first()


def get_user_by_id(user_id: int) -> User | None:
    """Ambil user berdasarkan primary key untuk proses internal Sentinel."""
    if not user_id:
        return None
    return db.session.get(User, user_id)


def upsert_user(
    *,
    channel_id: str,
    email: str | None = None,
    channel_title: str | None = None,
    thumbnail_url: str | None = None,
    refresh_token_plain: str = "",
) -> User:
    """Buat atau perbarui baris pengguna saat login OAuth.

    - ``refresh_token_plain`` dienkripsi dengan Fernet sebelum disimpan ke ``refresh_token_enc``.
    - Bila pengguna sudah ada dan ``refresh_token_plain`` kosong (misalnya saat login ulang
      Google tidak mengirim refresh token baru), ``refresh_token_enc`` lama tetap dipertahankan.
    """
    if not channel_id:
        raise ValueError("channel_id wajib diisi")

    user = get_user_by_channel_id(channel_id)
    encrypted = encrypt_token(refresh_token_plain) if refresh_token_plain else None
    now = datetime.now(UTC)

    if user is None:
        user = User(
            channel_id=channel_id,
            email=email,
            channel_title=channel_title,
            thumbnail_url=thumbnail_url,
            refresh_token_enc=encrypted,
            created_at=now,
            updated_at=now,
        )
        db.session.add(user)
    else:
        if email is not None:
            user.email = email
        if channel_title is not None:
            user.channel_title = channel_title
        if thumbnail_url is not None:
            user.thumbnail_url = thumbnail_url
        if encrypted:
            user.refresh_token_enc = encrypted
        user.updated_at = now

    db.session.commit()
    return user


def get_decrypted_refresh_token(channel_id: str) -> str:
    """Ambil dan dekripsi refresh token milik ``channel_id``."""
    user = get_user_by_channel_id(channel_id)
    if user is None or not user.refresh_token_enc:
        return ""
    return decrypt_token(user.refresh_token_enc)


def get_decrypted_refresh_token_by_user_id(user_id: int) -> str:
    """Ambil refresh token terenkripsi berdasarkan ``users.id``."""
    user = get_user_by_id(user_id)
    if user is None or not user.refresh_token_enc:
        return ""
    return decrypt_token(user.refresh_token_enc)


def clear_user_refresh_token(channel_id: str) -> None:
    """Hapus refresh token terenkripsi saat pengguna memutus akun."""
    user = get_user_by_channel_id(channel_id)
    if user is not None:
        user.refresh_token_enc = None
        user.updated_at = datetime.now(UTC)
        db.session.commit()


def delete_user_and_all_data(channel_id: str) -> bool:
    """Hapus pengguna beserta seluruh datanya (ON DELETE CASCADE, PRD 14.2)."""
    user = get_user_by_channel_id(channel_id)
    if user is None:
        return False
    db.session.delete(user)
    db.session.commit()
    return True
