"""Layanan Google OAuth 2.0 dan pengambilan channel YouTube (PRD Part 2 & 13.1-13.3)."""

from __future__ import annotations

from typing import Any

import requests
from flask import Flask

from ..extensions import oauth

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
YOUTUBE_FORCE_SSL_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
OAUTH_SCOPES = f"openid email profile {YOUTUBE_FORCE_SSL_SCOPE}"


class OAuthFlowError(Exception):
    """Galat selama proses pertukaran token atau pemanggilan API OAuth."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class NoYouTubeChannelError(OAuthFlowError):
    """Akun Google yang login belum memiliki channel YouTube."""

    def __init__(self) -> None:
        super().__init__(
            "no_youtube_channel",
            "Akun Google ini belum memiliki channel YouTube. Buat channel YouTube terlebih dahulu.",
            403,
        )


def init_oauth(app: Flask) -> None:
    """Daftarkan provider Google OAuth 2.0 pada instance Authlib."""
    oauth.register(
        name="google",
        client_id=app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url=GOOGLE_DISCOVERY_URL,
        authorize_url=GOOGLE_AUTH_URL,
        access_token_url=GOOGLE_TOKEN_URL,
        api_base_url="https://www.googleapis.com/",
        userinfo_endpoint=GOOGLE_USERINFO_URL,
        client_kwargs={"scope": OAUTH_SCOPES},
    )


def fetch_google_email(access_token: str, token_payload: dict[str, Any]) -> str:
    """Ambil alamat email pengguna dari payload ID token atau endpoint userinfo."""
    userinfo = token_payload.get("userinfo")
    if isinstance(userinfo, dict) and userinfo.get("email"):
        return str(userinfo["email"])

    resp = requests.get(
        GOOGLE_USERINFO_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept-Encoding": "gzip",
            "User-Agent": "JudolGuard/0.2 (gzip)",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise OAuthFlowError(
            "userinfo_failed",
            "Gagal mengambil informasi profil akun Google.",
            502,
        )
    data = resp.json()
    return str(data.get("email", ""))


def fetch_my_youtube_channel(access_token: str) -> dict[str, Any]:
    """Ambil channel_id dan detail channel milik pengguna via channels.list (mine=true).

    Memakai partial response (part & fields) serta kompresi gzip sesuai PRD 13.3.
    """
    resp = requests.get(
        YOUTUBE_CHANNELS_URL,
        params={
            "part": "snippet",
            "mine": "true",
            "fields": "items(id,snippet(title,customUrl,thumbnails/default/url))",
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept-Encoding": "gzip",
            "User-Agent": "JudolGuard/0.2 (gzip)",
        },
        timeout=15,
    )
    if resp.status_code == 401:
        raise OAuthFlowError("youtube_unauthorized", "Token OAuth YouTube tidak valid atau kedaluwarsa.", 401)
    if resp.status_code == 403:
        raise OAuthFlowError(
            "youtube_forbidden",
            "Akses ke YouTube Data API v3 ditolak. Pastikan YouTube Data API v3 aktif dan izin diberikan.",
            403,
        )
    if resp.status_code != 200:
        raise OAuthFlowError(
            "youtube_api_error",
            f"Gagal mengambil profil channel YouTube (HTTP {resp.status_code}).",
            502,
        )

    payload = resp.json()
    items = payload.get("items") or []
    if not items:
        raise NoYouTubeChannelError()

    first = items[0]
    snippet = first.get("snippet") or {}
    thumbnails = snippet.get("thumbnails") or {}
    default_thumb = thumbnails.get("default") or {}

    return {
        "channel_id": str(first["id"]),
        "channel_title": str(snippet.get("title", "Channel Tanpa Nama")),
        "custom_url": snippet.get("customUrl"),
        "thumbnail_url": str(default_thumb.get("url", "")),
    }
