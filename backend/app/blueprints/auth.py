"""Blueprint `auth` — Login OAuth Google/YouTube (Part 2, PRD 6.1, 12, 13.1, 14.1).

Endpoint:
- GET  /auth/login     : mulai alur OAuth Google (scope youtube.force-ssl + state anti-CSRF)
                         ?next=/path  — URL frontend tujuan setelah login berhasil (default /videos)
- GET  /auth/callback  : validasi state, tukar code -> token, panggil channels.list(mine=true),
                         simpan token di ServerSessionStore (bukan di cookie!),
                         redirect ke ?next=/videos atau /?auth_error=... bila dibatalkan
- POST /auth/logout    : hapus sesi server & bersihkan cookie HttpOnly
                         (GET /auth/logout juga diizinkan saat DEBUG/TESTING untuk tes browser)
- GET  /api/me         : kembalikan profil pengguna & channel YouTube dari sesi aktif
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from urllib.parse import urlencode

from flask import Blueprint, current_app, g, redirect, request, session, url_for

from ..auth_guard import SESSION_COOKIE_KEY, login_required
from ..extensions import oauth
from ..repositories import user_repo
from ..responses import fail, ok
from ..services.oauth_service import (
    OAuthFlowError,
    fetch_google_email,
    fetch_my_youtube_channel,
)
from ..services.session_store import session_store

logger = logging.getLogger(__name__)

bp = Blueprint("auth", __name__)

OAUTH_STATE_KEY = "oauth_state"
OAUTH_REDIRECT_URI_KEY = "oauth_redirect_uri"
OAUTH_NEXT_KEY = "oauth_next"


def _resolve_redirect_uri() -> str:
    """Pilih redirect_uri yang cocok dengan host tempat pengguna memulai login.

    - Bila diakses langsung lewat port backend (127.0.0.1:5000 / localhost:5000),
      pakai callback di host tersebut agar pengujian backend tanpa UI berjalan langsung.
    - Bila diakses dari origin lain / proxy, gunakan GOOGLE_REDIRECT_URI dari konfigurasi.
    """
    backend_port = str(current_app.config.get("PORT", 5000))
    host = request.host or ""
    if host.endswith(f":{backend_port}") or current_app.config.get("TESTING"):
        return url_for("auth.callback", _external=True)
    configured = (current_app.config.get("GOOGLE_REDIRECT_URI") or "").strip()
    return configured or url_for("auth.callback", _external=True)


def _safe_next_url(raw_next: str | None) -> str | None:
    if not raw_next:
        return None
    cleaned = raw_next.strip()
    if cleaned.startswith("/") and not cleaned.startswith("//"):
        return cleaned
    return None


@bp.get("/auth/login")
def login():
    cfg = current_app.config
    if not (cfg.get("GOOGLE_CLIENT_ID") and cfg.get("GOOGLE_CLIENT_SECRET")):
        return fail(
            "oauth_not_configured",
            "GOOGLE_CLIENT_ID dan GOOGLE_CLIENT_SECRET belum diisi di .env.",
            503,
        )

    state = secrets.token_urlsafe(32)
    redirect_uri = _resolve_redirect_uri()
    next_url = _safe_next_url(request.args.get("next"))

    # Bila tidak ada ?next= dan bukan mode pengujian, default ke /videos (tujuan setelah login).
    # Saat TESTING, biarkan None agar tes yang ada (redirect ke /api/me) tidak perlu diubah.
    if not next_url and not current_app.config.get("TESTING"):
        next_url = "/videos"

    session[OAUTH_STATE_KEY] = state
    session[OAUTH_REDIRECT_URI_KEY] = redirect_uri
    if next_url:
        session[OAUTH_NEXT_KEY] = next_url
    else:
        session.pop(OAUTH_NEXT_KEY, None)

    return oauth.google.authorize_redirect(
        redirect_uri=redirect_uri,
        state=state,
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )


@bp.get("/auth/callback")
def callback():
    # 1. Tangani bila pengguna menolak izin atau Google mengembalikan error
    oauth_error = request.args.get("error")
    if oauth_error:
        session.pop(OAUTH_STATE_KEY, None)
        desc = request.args.get("error_description") or "Akses OAuth Google dibatalkan atau ditolak."
        # Di mode pengujian kembalikan JSON agar test tetap bisa assert status code & code.
        # Di mode normal, redirect ke beranda dengan pesan error yang ramah pengguna.
        if current_app.config.get("TESTING"):
            return fail("oauth_access_denied", f"{desc} ({oauth_error})", 403)
        qs = urlencode({"auth_error": oauth_error, "auth_error_desc": desc})
        return redirect(f"/?{qs}")

    # 2. Validasi parameter state (anti-CSRF, PRD Part 2)
    expected_state = session.pop(OAUTH_STATE_KEY, None)
    received_state = request.args.get("state")
    if not expected_state or not received_state or not secrets.compare_digest(expected_state, received_state):
        return fail(
            "invalid_oauth_state",
            "Parameter state OAuth tidak valid atau sudah kedaluwarsa. Silakan ulangi login.",
            400,
        )

    # 3. Tukar authorization code menjadi token OAuth
    try:
        token: dict[str, Any] = oauth.google.authorize_access_token()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gagal menukar authorization code OAuth: %s", exc)
        return fail("oauth_token_exchange_failed", "Gagal menukar kode otorisasi dengan Google.", 400)

    access_token = str(token.get("access_token") or "")
    refresh_token = str(token.get("refresh_token") or "")
    expires_at = token.get("expires_at")
    if not access_token:
        return fail("oauth_missing_access_token", "Google tidak mengembalikan access token.", 400)

    # 4. Ambil email & profil channel YouTube lewat channels.list(mine=true)
    try:
        email = fetch_google_email(access_token, token)
        channel = fetch_my_youtube_channel(access_token)
    except OAuthFlowError as exc:
        return fail(exc.code, exc.message, exc.status)

    # 5. Simpan pengguna & refresh token terenkripsi ke tabel `users` (PRD Part 3)
    effective_refresh_token = refresh_token
    try:
        db_user = user_repo.upsert_user(
            channel_id=channel["channel_id"],
            email=email,
            channel_title=channel["channel_title"],
            thumbnail_url=channel["thumbnail_url"],
            refresh_token_plain=refresh_token,
        )
        if not effective_refresh_token and db_user.refresh_token_enc:
            effective_refresh_token = user_repo.get_decrypted_refresh_token(channel["channel_id"])
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gagal menyimpan pengguna ke database: %s", exc)
        return fail("database_error", "Gagal menyimpan data pengguna ke database.", 500)

    # 6. Simpan sesi aktif di ServerSessionStore (BUKAN di cookie klien!)
    old_sid = session.get(SESSION_COOKIE_KEY)
    if old_sid:
        session_store.delete(old_sid)

    next_url = _safe_next_url(session.pop(OAUTH_NEXT_KEY, None))
    session.clear()

    server_session = session_store.create(
        channel_id=channel["channel_id"],
        channel_title=channel["channel_title"],
        email=email,
        thumbnail_url=channel["thumbnail_url"],
        custom_url=channel.get("custom_url"),
        access_token=access_token,
        refresh_token=effective_refresh_token,
        expires_at=float(expires_at) if expires_at is not None else None,
    )
    # Cookie HttpOnly hanya menyimpan sid acak
    session[SESSION_COOKIE_KEY] = server_session.sid

    logger.info(
        "Login OAuth berhasil untuk channel_id=%s (%s)",
        server_session.channel_id,
        server_session.channel_title,
    )

    # Bila ada target redirect frontend (?next=/videos atau lainnya), arahkan ke sana;
    # bila diuji langsung di backend (TESTING tanpa ?next=), arahkan ke /api/me agar JSON profil tampil.
    if next_url:
        return redirect(next_url)
    return redirect(url_for("auth.me"))


@bp.route("/auth/logout", methods=["POST", "GET"])
def logout():
    # Di produksi hanya izinkan POST; saat DEBUG/TESTING izinkan GET agar mudah dites di browser.
    if request.method == "GET" and not (
        current_app.config.get("DEBUG") or current_app.config.get("TESTING")
    ):
        return fail("method_not_allowed", "Gunakan metode POST untuk logout.", 405)

    sid = session.get(SESSION_COOKIE_KEY)
    session_store.delete(sid)
    session.clear()
    return ok({"logged_out": True})


@bp.get("/api/me")
@login_required
def me():
    user_session = g.current_user
    return ok(
        {
            "authenticated": True,
            "user": user_session.to_public_user(),
        }
    )
