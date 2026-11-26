"""Uji refresh access token Google tanpa request network sungguhan."""

from __future__ import annotations

from datetime import UTC

import pytest
import requests

from app.repositories import user_repo
from app.services.google_token import (
    GoogleOAuthConfigurationError,
    GoogleTokenResponseError,
    InvalidGrantError,
    MissingRefreshTokenError,
    refresh_access_token,
)


class _FakeResponse:
    def __init__(
        self,
        payload: dict[str, object],
        *,
        status_code: int = 200,
        ok: bool = True,
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self.ok = ok

    def json(self) -> dict[str, object]:
        return self._payload


def _seed_user(app, refresh_token: str = "refresh-token-test"):
    with app.app_context():
        user = user_repo.upsert_user(
            channel_id="UC_TOKEN_TEST",
            email="token@example.com",
            refresh_token_plain=refresh_token,
        )
        return user.id


def test_refresh_access_token_success_does_not_persist_access_token(app, monkeypatch):
    user_id = _seed_user(app)
    fake_access_token = "access-token-must-stay-in-memory"
    captured: dict[str, object] = {}

    def fake_post(url, *, data, timeout):
        captured.update({"url": url, "data": data, "timeout": timeout})
        return _FakeResponse({"access_token": fake_access_token, "expires_in": 3600})

    monkeypatch.setattr("app.services.google_token.requests.post", fake_post)
    result = refresh_access_token(app, user_id, timeout=9, retries=0)

    assert result.access_token == fake_access_token
    assert result.expires_in == 3600
    assert result.expires_at.tzinfo == UTC
    assert captured["timeout"] == 9
    assert captured["data"]["grant_type"] == "refresh_token"
    assert captured["data"]["refresh_token"] == "refresh-token-test"

    with app.app_context():
        stored = user_repo.get_user_by_id(user_id)
        assert stored is not None
        assert stored.refresh_token_enc != fake_access_token
        assert stored.refresh_token_enc != "refresh-token-test"


def test_refresh_access_token_rejects_missing_refresh_token(app, monkeypatch):
    user_id = _seed_user(app, refresh_token="")
    monkeypatch.setattr(
        "app.services.google_token.requests.post",
        lambda *args, **kwargs: pytest.fail("Google tidak boleh dipanggil"),
    )

    with pytest.raises(MissingRefreshTokenError):
        refresh_access_token(app, user_id)


def test_refresh_access_token_handles_invalid_grant(app, monkeypatch):
    user_id = _seed_user(app)
    monkeypatch.setattr(
        "app.services.google_token.requests.post",
        lambda *args, **kwargs: _FakeResponse(
            {"error": "invalid_grant"},
            status_code=400,
            ok=False,
        ),
    )

    with pytest.raises(InvalidGrantError):
        refresh_access_token(app, user_id, retries=2)


def test_refresh_access_token_retries_network_error(app, monkeypatch):
    user_id = _seed_user(app)
    responses = iter(
        [
            requests.ConnectionError("temporary"),
            _FakeResponse({"access_token": "access-after-retry", "expires_in": 120}),
        ]
    )
    calls = 0
    monkeypatch.setattr("app.services.google_token.time.sleep", lambda *_: None)

    def fake_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr("app.services.google_token.requests.post", fake_post)
    result = refresh_access_token(app, user_id, retries=1)

    assert result.access_token == "access-after-retry"
    assert calls == 2


def test_refresh_access_token_rejects_invalid_response(app, monkeypatch):
    user_id = _seed_user(app)
    monkeypatch.setattr(
        "app.services.google_token.requests.post",
        lambda *args, **kwargs: _FakeResponse({"expires_in": 3600}),
    )

    with pytest.raises(GoogleTokenResponseError):
        refresh_access_token(app, user_id)


def test_refresh_access_token_requires_google_configuration(app, monkeypatch):
    user_id = _seed_user(app)
    monkeypatch.setitem(app.config, "GOOGLE_CLIENT_ID", "")

    with pytest.raises(GoogleOAuthConfigurationError):
        refresh_access_token(app, user_id)
