"""Uji pairing Telegram melalui web dan deep link /start."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from app.extensions import db
from app.models import PairingToken, TelegramLink, User
from app.services.session_store import session_store
from app.services.telegram_pairing import PairingError, consume_pairing_token


def _authenticate(client, channel_id: str) -> None:
    server_session = session_store.create(
        channel_id=channel_id,
        channel_title="Channel Pairing",
        email="pairing@example.com",
        access_token="fake-access-token",
    )
    with client.session_transaction() as flask_session:
        flask_session["sid"] = server_session.sid


def _seed_user(app, channel_id: str) -> User:
    with app.app_context():
        user = User(channel_id=channel_id, email="pairing@example.com")
        db.session.add(user)
        db.session.commit()
        return user


def test_pairing_endpoint_creates_deep_link_and_status(client, app):
    _seed_user(app, "UC_PAIRING_OWNER")
    _authenticate(client, "UC_PAIRING_OWNER")
    app.config["TELEGRAM_BOT_USERNAME"] = "judolguard_sentinel_bot"

    response = client.post("/api/telegram/pairing")

    assert response.status_code == 200
    data = response.get_json()["data"]
    parsed = urlparse(data["pairing_url"])
    raw_token = parse_qs(parsed.query)["start"][0]
    assert parsed.netloc == "t.me"
    assert parsed.path == "/judolguard_sentinel_bot"
    assert len(raw_token) > 20
    assert data["expires_in"] == 600

    with app.app_context():
        stored = db.session.query(PairingToken).one()
        assert stored.token_hash != raw_token
        assert len(stored.token_hash) == 64

    status = client.get("/api/telegram/status")
    assert status.status_code == 200
    assert status.get_json()["data"]["connected"] is False

    with app.app_context():
        user = db.session.query(User).filter_by(channel_id="UC_PAIRING_OWNER").one()
        consume_pairing_token(raw_token, 123456789)
        link = db.session.query(TelegramLink).one()
        assert link.user_id == user.id
        assert link.chat_id == 123456789

    status = client.get("/api/telegram/status")
    assert status.get_json()["data"]["connected"] is True
    assert status.get_json()["data"]["chat_id_masked"] == "****6789"

    with app.app_context(), pytest.raises(PairingError, match="tidak valid"):
        consume_pairing_token(raw_token, 123456789)


def test_pairing_token_expiry_and_chat_ownership(app):
    with app.app_context():
        owner = User(channel_id="UC_PAIRING_OWNER_2")
        other = User(channel_id="UC_PAIRING_OWNER_3")
        db.session.add_all([owner, other])
        db.session.flush()
        expired = PairingToken(
            token_hash=hashlib.sha256(b"raw-expired-token").hexdigest(),
            user_id=owner.id,
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.session.add(expired)
        db.session.commit()

        with pytest.raises(PairingError, match="kedaluwarsa"):
            consume_pairing_token("raw-expired-token", 987)

        valid_token = "c" * 64
        db.session.add(
            PairingToken(
                token_hash=hashlib.sha256(valid_token.encode("utf-8")).hexdigest(),
                user_id=owner.id,
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
            )
        )
        db.session.add(TelegramLink(user_id=other.id, chat_id=987))
        db.session.commit()

        with pytest.raises(PairingError, match="sudah terhubung"):
            consume_pairing_token(valid_token, 987)
