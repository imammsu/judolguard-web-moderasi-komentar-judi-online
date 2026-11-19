"""Penyimpanan sesi OAuth di sisi server (PRD Part 2 & 14.1).

Aturan keamanan PRD 14.1:
- Token OAuth TIDAK pernah disimpan di cookie sesi bawaan Flask maupun di klien.
- Cookie HttpOnly di browser hanya memegang ``sid`` (ID sesi acak).
- ``refresh_token`` disimpan dalam bentuk terenkripsi Fernet (``refresh_token_enc``).
- Pada Part 3, penyimpanan permanen pengguna & refresh token akan dihubungkan
  ke tabel ``users`` di PostgreSQL Supabase.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any

from .crypto import decrypt_token, encrypt_token


@dataclass
class ServerSession:
    sid: str
    channel_id: str
    channel_title: str
    email: str
    thumbnail_url: str
    custom_url: str | None
    access_token: str
    refresh_token_enc: str
    expires_at: float | None
    created_at: float

    @property
    def refresh_token(self) -> str:
        return decrypt_token(self.refresh_token_enc) if self.refresh_token_enc else ""

    def to_public_user(self) -> dict[str, Any]:
        """Representasi profil pengguna yang aman dikirim ke JSON API (tanpa token)."""
        return {
            "channel_id": self.channel_id,
            "channel_title": self.channel_title,
            "email": self.email,
            "thumbnail_url": self.thumbnail_url,
            "custom_url": self.custom_url,
        }


class ServerSessionStore:
    """Penyimpanan sesi sisi server yang thread-safe."""

    def __init__(self) -> None:
        self._sessions: dict[str, ServerSession] = {}
        self._lock = threading.Lock()

    def create(
        self,
        *,
        channel_id: str,
        channel_title: str,
        email: str,
        thumbnail_url: str = "",
        custom_url: str | None = None,
        access_token: str,
        refresh_token: str = "",
        expires_at: float | None = None,
    ) -> ServerSession:
        sid = secrets.token_urlsafe(32)
        entry = ServerSession(
            sid=sid,
            channel_id=channel_id,
            channel_title=channel_title,
            email=email,
            thumbnail_url=thumbnail_url,
            custom_url=custom_url,
            access_token=access_token,
            refresh_token_enc=encrypt_token(refresh_token) if refresh_token else "",
            expires_at=expires_at,
            created_at=time.time(),
        )
        with self._lock:
            self._sessions[sid] = entry
        return entry

    def get(self, sid: str | None) -> ServerSession | None:
        if not sid:
            return None
        with self._lock:
            return self._sessions.get(sid)

    def delete(self, sid: str | None) -> None:
        if not sid:
            return
        with self._lock:
            self._sessions.pop(sid, None)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


session_store = ServerSessionStore()
