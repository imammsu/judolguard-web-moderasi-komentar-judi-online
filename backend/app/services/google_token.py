"""Refresh access token Google untuk proses Sentinel."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from flask import Flask

from ..repositories import user_repo
from .oauth_service import GOOGLE_TOKEN_URL

logger = logging.getLogger(__name__)


class GoogleTokenError(Exception):
    """Base error yang aman diteruskan ke caller Sentinel."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class MissingRefreshTokenError(GoogleTokenError):
    def __init__(self) -> None:
        super().__init__(
            "missing_refresh_token",
            "Refresh token Google belum tersedia. Silakan login ulang.",
        )


class InvalidGrantError(GoogleTokenError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_grant",
            "Akses Google telah dicabut atau kedaluwarsa. Silakan login ulang.",
        )


class GoogleOAuthConfigurationError(GoogleTokenError):
    def __init__(self) -> None:
        super().__init__(
            "google_oauth_not_configured",
            "Google OAuth belum dikonfigurasi dengan lengkap.",
        )


class GoogleTokenNetworkError(GoogleTokenError):
    def __init__(self) -> None:
        super().__init__(
            "google_token_network_error",
            "Layanan token Google tidak dapat dihubungi.",
            retryable=True,
        )


class GoogleTokenResponseError(GoogleTokenError):
    def __init__(self) -> None:
        super().__init__(
            "google_token_response_error",
            "Respons token Google tidak valid.",
        )


@dataclass(frozen=True)
class AccessTokenResult:
    access_token: str
    expires_at: datetime
    expires_in: int


def _error_code(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    return str(payload.get("error") or "") if isinstance(payload, dict) else ""


def _request_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
    timeout: int,
    retries: int,
) -> dict[str, Any]:
    attempts = max(0, retries) + 1
    for attempt in range(attempts):
        try:
            response = requests.post(
                GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=max(1, timeout),
            )
        except requests.RequestException as exc:
            if attempt < attempts - 1:
                time.sleep(min(2**attempt, 4))
                continue
            raise GoogleTokenNetworkError() from exc

        if response.status_code in {429, 500, 502, 503, 504}:
            if attempt < attempts - 1:
                time.sleep(min(2**attempt, 4))
                continue
            raise GoogleTokenNetworkError()

        if _error_code(response) == "invalid_grant":
            raise InvalidGrantError()

        if not response.ok:
            raise GoogleTokenResponseError()

        try:
            payload = response.json()
        except ValueError as exc:
            raise GoogleTokenResponseError() from exc
        if not isinstance(payload, dict):
            raise GoogleTokenResponseError()
        return payload

    # Loop selalu return atau raise; ini hanya pengaman untuk static analysis.
    raise GoogleTokenNetworkError()


def refresh_access_token(
    app: Flask,
    user_id: int,
    *,
    timeout: int = 15,
    retries: int = 2,
) -> AccessTokenResult:
    """Tukar refresh token milik user menjadi access token sementara."""
    with app.app_context():
        refresh_token = user_repo.get_decrypted_refresh_token_by_user_id(user_id)
        if not refresh_token:
            raise MissingRefreshTokenError()

        client_id = str(app.config.get("GOOGLE_CLIENT_ID") or "")
        client_secret = str(app.config.get("GOOGLE_CLIENT_SECRET") or "")
        if not client_id or not client_secret:
            raise GoogleOAuthConfigurationError()

        payload = _request_access_token(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            timeout=timeout,
            retries=retries,
        )

    access_token = str(payload.get("access_token") or "")
    try:
        expires_in = int(payload.get("expires_in") or 0)
    except (TypeError, ValueError) as exc:
        raise GoogleTokenResponseError() from exc
    if not access_token or expires_in <= 0:
        raise GoogleTokenResponseError()

    return AccessTokenResult(
        access_token=access_token,
        expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        expires_in=expires_in,
    )
