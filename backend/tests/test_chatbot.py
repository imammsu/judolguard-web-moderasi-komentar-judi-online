"""Uji tool read-only dan endpoint chatbot."""

from __future__ import annotations

from datetime import UTC, datetime

from app.extensions import db
from app.models import ChatLog, ChatSession, Comment, Keyword, Video
from app.services.chatbot_tools import count_judol, top_spammers
from app.services.llm import LLMChatUnavailable
from app.services.session_store import session_store


def _authenticate(client, channel_id: str = "UC_CHAT_OWNER") -> None:
    server_session = session_store.create(
        channel_id=channel_id,
        channel_title="Pemilik Chat",
        email="chat@example.com",
        access_token="fake-access-token",
    )
    with client.session_transaction() as flask_session:
        flask_session["sid"] = server_session.sid


def _seed_chat_data(app) -> None:
    with app.app_context():
        db.session.add_all(
            [
                Video(
                    video_id="chat-video",
                    owner_channel_id="UC_CHAT_OWNER",
                    title="Video Chat",
                    comment_count=3,
                ),
                Comment(
                    comment_id="chat-comment-1",
                    video_id="chat-video",
                    owner_channel_id="UC_CHAT_OWNER",
                    author_channel_id="UC_SPAMMER",
                    author_name="Akun Spam",
                    text_original="Daftar GACOR77",
                    zone="judol",
                    classified_at=datetime.now(UTC),
                ),
                Comment(
                    comment_id="chat-comment-2",
                    video_id="chat-video",
                    owner_channel_id="UC_CHAT_OWNER",
                    author_channel_id="UC_SPAMMER",
                    author_name="Akun Spam",
                    text_original="Bonus di GACOR77",
                    zone="judol",
                    classified_at=datetime.now(UTC),
                ),
                Comment(
                    comment_id="chat-comment-3",
                    video_id="chat-video",
                    owner_channel_id="UC_CHAT_OWNER",
                    author_channel_id="UC_NORMAL",
                    author_name="Akun Normal",
                    text_original="Komentar biasa",
                    zone="bukan",
                    classified_at=datetime.now(UTC),
                ),
                Keyword(
                    video_id="chat-video",
                    owner_channel_id="UC_CHAT_OWNER",
                    keyword="GACOR77",
                    type="situs",
                    frequency=2,
                ),
            ]
        )
        db.session.commit()


def test_chatbot_tools_filter_owner_and_return_aggregates(app):
    _seed_chat_data(app)
    with app.app_context():
        spammers = top_spammers("UC_CHAT_OWNER", video_id="chat-video")
        counts = count_judol("UC_CHAT_OWNER", video_id="chat-video")

    assert spammers["items"][0]["author_channel_id"] == "UC_SPAMMER"
    assert spammers["items"][0]["comment_count"] == 2
    assert counts["classified_comments"] == 3
    assert counts["judol_comments"] == 2
    assert counts["judol_percentage"] == 66.67
    with app.app_context():
        assert top_spammers("UC_OTHER_OWNER")["total"] == 0


def test_chat_endpoint_returns_answer_without_exposing_provider_error(
    client,
    app,
    monkeypatch,
):
    _authenticate(client)
    _seed_chat_data(app)
    monkeypatch.setattr(
        "app.services.chatbot.chat_with_tools",
        lambda *args, **kwargs: (
            "Akun UC_SPAMMER memiliki 2 komentar judol.",
            ["top_spammers"],
            "gemini",
            "gemini-3.5-flash-lite",
        ),
    )

    response = client.post(
        "/api/chat",
        json={
            "question": "Akun mana yang paling sering spam?",
            "video_id": "chat-video",
            "history": [],
        },
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["answer"].startswith("Akun UC_SPAMMER")
    assert data["tool_used"] == ["top_spammers"]
    assert data["provider"] == "gemini"
    with app.app_context():
        log = db.session.query(ChatLog).one()
        assert log.owner_channel_id == "UC_CHAT_OWNER"
        assert log.question == "Akun mana yang paling sering spam?"
        assert log.tool_used == "top_spammers"

    history = client.get("/api/chat/history")
    assert history.status_code == 200
    history_data = history.get_json()["data"]
    assert history_data["total"] == 1
    assert history_data["items"][0]["question"] == "Akun mana yang paling sering spam?"
    assert history_data["items"][0]["tool_used"] == ["top_spammers"]


def test_chat_endpoint_validates_request(client):
    _authenticate(client)
    response = client.post("/api/chat", json={"question": ""})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_chat_endpoint_uses_safe_fallback_when_providers_fail(
    client,
    app,
    monkeypatch,
):
    _authenticate(client)
    monkeypatch.setattr(
        "app.services.chatbot.chat_with_tools",
        lambda *args, **kwargs: (_ for _ in ()).throw(LLMChatUnavailable([])),
    )

    response = client.post(
        "/api/chat",
        json={"question": "Berapa jumlah komentar judol?"},
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["fallback"] is True
    assert "tidak tersedia" in data["answer"].lower()


def test_chat_sessions_isolate_messages_by_owner_and_session(client, app, monkeypatch):
    _authenticate(client)
    _seed_chat_data(app)
    monkeypatch.setattr(
        "app.services.chatbot.chat_with_tools",
        lambda *args, **kwargs: (
            "Jawaban sesi.",
            ["count_judol"],
            "gemini",
            "gemini-test",
        ),
    )

    created = client.post("/api/chat/sessions", json={"video_id": "chat-video"})
    assert created.status_code == 201
    session = created.get_json()["data"]
    session_id = session["id"]
    assert session["video_id"] == "chat-video"

    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "question": "Berapa jumlah komentar judol?"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["session_id"] == session_id

    messages = client.get(f"/api/chat/sessions/{session_id}/messages")
    assert messages.status_code == 200
    assert messages.get_json()["data"]["total"] == 1

    other_client = app.test_client()
    _authenticate(other_client, "UC_OTHER_OWNER")
    assert other_client.get(f"/api/chat/sessions/{session_id}/messages").status_code == 404
    assert other_client.delete(f"/api/chat/sessions/{session_id}").status_code == 404

    with app.app_context():
        assert db.session.query(ChatSession).count() == 1
        log = db.session.query(ChatLog).one()
        assert log.session_id is not None
