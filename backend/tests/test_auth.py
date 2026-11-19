"""Uji Part 2: Backend OAuth Google/YouTube, penyimpanan sesi sisi server, & /api/me."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from app.extensions import oauth
from app.services.oauth_service import YOUTUBE_FORCE_SSL_SCOPE, NoYouTubeChannelError
from app.services.session_store import session_store


@pytest.fixture(autouse=True)
def _clean_session_store():
    session_store.clear()
    yield
    session_store.clear()


def test_api_me_unauthenticated_returns_401(client):
    res = client.get("/api/me")
    assert res.status_code == 401
    body = res.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "unauthorized"


def test_auth_login_redirects_to_google_with_state_and_scope(client):
    res = client.get("/auth/login")
    assert res.status_code == 302
    location = res.headers["Location"]
    parsed = urlparse(location)
    assert parsed.netloc == "accounts.google.com"
    query = parse_qs(parsed.query)
    assert "state" in query and len(query["state"][0]) >= 20
    assert query.get("access_type") == ["offline"]
    assert query.get("prompt") == ["consent"]
    assert YOUTUBE_FORCE_SSL_SCOPE in query.get("scope", [""])[0]


def test_auth_callback_rejects_missing_or_mismatched_state(client):
    # State di query tidak cocok dengan state di session cookie
    res = client.get("/auth/callback?code=fake-code&state=wrong-state")
    assert res.status_code == 400
    body = res.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "invalid_oauth_state"


def test_auth_callback_handles_google_access_denied(client):
    res = client.get("/auth/callback?error=access_denied&error_description=User+cancelled")
    assert res.status_code == 403
    body = res.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "oauth_access_denied"


def test_auth_callback_rejects_user_without_youtube_channel(client, monkeypatch):
    # Mulai login agar state tersimpan di sesi
    login_res = client.get("/auth/login")
    state = parse_qs(urlparse(login_res.headers["Location"]).query)["state"][0]

    monkeypatch.setattr(
        oauth.google,
        "authorize_access_token",
        lambda: {
            "access_token": "ya29.fake-access-token",
            "refresh_token": "1//fake-refresh-token",
            "userinfo": {"email": "nochannel@example.com"},
        },
    )

    def _raise_no_channel(_access_token: str):
        raise NoYouTubeChannelError()

    monkeypatch.setattr("app.blueprints.auth.fetch_my_youtube_channel", _raise_no_channel)

    res = client.get(f"/auth/callback?code=valid-code&state={state}")
    assert res.status_code == 403
    body = res.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "no_youtube_channel"


def test_auth_callback_success_stores_tokens_server_side_and_not_in_cookie(client, monkeypatch):
    # 1. Mulai login
    login_res = client.get("/auth/login")
    state = parse_qs(urlparse(login_res.headers["Location"]).query)["state"][0]

    fake_access_token = "ya29.SECRET_ACCESS_TOKEN_DO_NOT_LEAK"
    fake_refresh_token = "1//SECRET_REFRESH_TOKEN_DO_NOT_LEAK"

    monkeypatch.setattr(
        oauth.google,
        "authorize_access_token",
        lambda: {
            "access_token": fake_access_token,
            "refresh_token": fake_refresh_token,
            "expires_at": 1899999999,
            "userinfo": {"email": "creator@example.com"},
        },
    )
    monkeypatch.setattr(
        "app.blueprints.auth.fetch_my_youtube_channel",
        lambda _token: {
            "channel_id": "UC_JUDOLGUARD_TEST_01",
            "channel_title": "Channel Creator Uji",
            "custom_url": "@creatoruji",
            "thumbnail_url": "https://yt3.ggpht.com/test-thumb.jpg",
        },
    )

    # 2. Panggil callback dengan state yang benar
    cb_res = client.get(f"/auth/callback?code=valid-code&state={state}")
    assert cb_res.status_code == 302
    assert cb_res.headers["Location"].endswith("/api/me")

    # 3. Verifikasi keamanan cookie (PRD 14.1):
    #    Cookie sesi Flask TIDAK boleh memuat access_token maupun refresh_token!
    set_cookie_header = cb_res.headers.get("Set-Cookie", "")
    assert "HttpOnly" in set_cookie_header
    assert fake_access_token not in set_cookie_header
    assert fake_refresh_token not in set_cookie_header

    with client.session_transaction() as flask_sess:
        assert "sid" in flask_sess
        assert "access_token" not in flask_sess
        assert "refresh_token" not in flask_sess
        sid = flask_sess["sid"]

    # 4. Verifikasi token tersimpan di ServerSessionStore dan refresh_token terenkripsi Fernet
    stored = session_store.get(sid)
    assert stored is not None
    assert stored.channel_id == "UC_JUDOLGUARD_TEST_01"
    assert stored.access_token == fake_access_token
    assert stored.refresh_token_enc != fake_refresh_token
    assert stored.refresh_token == fake_refresh_token

    # 5. Panggil /api/me -> harus mengembalikan profil channel tanpa membocorkan token
    me_res = client.get("/api/me")
    assert me_res.status_code == 200
    me_body = me_res.get_json()
    assert me_body["success"] is True
    assert me_body["data"]["authenticated"] is True
    user = me_body["data"]["user"]
    assert user["channel_id"] == "UC_JUDOLGUARD_TEST_01"
    assert user["channel_title"] == "Channel Creator Uji"
    assert user["email"] == "creator@example.com"
    assert "access_token" not in user
    assert "refresh_token" not in user

    # 6. Logout -> hapus sesi server & cookie
    logout_res = client.post("/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.get_json()["data"]["logged_out"] is True
    assert session_store.get(sid) is None

    # 7. Panggil /api/me setelah logout -> kembali 401
    after_res = client.get("/api/me")
    assert after_res.status_code == 401
