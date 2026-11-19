"""Middleware autentikasi dan decorator @login_required (PRD 12 & 14.1)."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import g, session

from .responses import fail
from .services.session_store import ServerSession, session_store

SESSION_COOKIE_KEY = "sid"


def get_current_session() -> ServerSession | None:
    """Ambil sesi aktif dari ServerSessionStore berdasarkan sid di cookie HttpOnly."""
    sid = session.get(SESSION_COOKIE_KEY)
    if not sid:
        return None
    server_session = session_store.get(sid)
    if server_session is None:
        # Sesi di server sudah tidak ada (mis. server restart atau sudah logout)
        session.pop(SESSION_COOKIE_KEY, None)
        return None
    return server_session


def login_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Pastikan endpoint hanya bisa diakses oleh pengguna yang sudah login OAuth."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any):
        current = get_current_session()
        if current is None:
            return fail("unauthorized", "Silakan login terlebih dahulu.", 401)
        g.current_user = current
        g.owner_channel_id = current.channel_id
        return fn(*args, **kwargs)

    return wrapper
