"""Uji ekstraksi keyword dari komentar judol hasil scan."""

from __future__ import annotations

from datetime import UTC, datetime

from app.extensions import db
from app.models import Comment, Job, Keyword, Video
from app.services.llm import (
    ExtractedItem,
    ExtractedKeyword,
    ExtractionResponse,
    LLMExtractionResult,
)
from app.services.session_store import session_store


def _authenticate(client, channel_id: str = "UC_KEYWORD_OWNER") -> None:
    server_session = session_store.create(
        channel_id=channel_id,
        channel_title="Pemilik Keyword",
        email="keyword@example.com",
        access_token="fake-access-token",
    )
    with client.session_transaction() as flask_session:
        flask_session["sid"] = server_session.sid


def _seed_video(app, owner: str = "UC_KEYWORD_OWNER") -> None:
    with app.app_context():
        db.session.add(
            Video(
                video_id="keyword-video",
                owner_channel_id=owner,
                title="Video Keyword",
                comment_count=10,
                last_fetched_at=datetime.now(UTC),
            )
        )
        db.session.add_all(
            [
                Comment(
                    comment_id="judol-1",
                    video_id="keyword-video",
                    owner_channel_id=owner,
                    text_original="Daftar di GACOR77 bonus sekarang",
                    zone="judol",
                    classified_at=datetime.now(UTC),
                ),
                Comment(
                    comment_id="judol-2",
                    video_id="keyword-video",
                    owner_channel_id=owner,
                    text_original="Daftar di GACOR77 bonus sekarang",
                    zone="judol",
                    classified_at=datetime.now(UTC),
                ),
                Comment(
                    comment_id="review-1",
                    video_id="keyword-video",
                    owner_channel_id=owner,
                    text_original="Link BETKLIK perlu direview",
                    zone="review",
                    classified_at=datetime.now(UTC),
                ),
                Comment(
                    comment_id="rejected-1",
                    video_id="keyword-video",
                    owner_channel_id=owner,
                    text_original="Daftar di REJECTED88",
                    zone="judol",
                    moderation_status="rejected",
                    classified_at=datetime.now(UTC),
                ),
                Job(
                    owner_channel_id=owner,
                    type="scan",
                    video_id="keyword-video",
                    status="done",
                    progress=100,
                    total=4,
                    processed=4,
                ),
            ]
        )
        db.session.commit()


def test_extract_keywords_uses_only_judol_and_persists_frequency(client, app, monkeypatch):
    _authenticate(client)
    _seed_video(app)
    monkeypatch.setattr(
        "app.services.extractor.extract_with_fallback",
        lambda items, **kwargs: LLMExtractionResult(
            response=ExtractionResponse(
                items=[
                    ExtractedItem(
                        source_id=1,
                        keywords=[
                            ExtractedKeyword(keyword="GACOR77", type="situs"),
                            ExtractedKeyword(keyword="tidak-ada", type="situs"),
                        ],
                    )
                ]
            ),
            provider="gemini",
            model="gemini-3.5-flash-lite",
        ),
    )

    response = client.post("/api/videos/keyword-video/keywords/extract")
    assert response.status_code == 202
    assert response.get_json()["data"]["status"] == "done"

    keywords = client.get("/api/videos/keyword-video/keywords")
    assert keywords.status_code == 200
    data = keywords.get_json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["keyword"] == "GACOR77"
    assert data["items"][0]["frequency"] == 2

    with app.app_context():
        assert db.session.query(Keyword).count() == 1


def test_extract_keywords_requires_completed_scan(client, app):
    _authenticate(client)
    with app.app_context():
        db.session.add(
            Video(
                video_id="unscanned-keyword-video",
                owner_channel_id="UC_KEYWORD_OWNER",
                title="Belum Scan",
                last_fetched_at=datetime.now(UTC),
            )
        )
        db.session.commit()

    response = client.post("/api/videos/unscanned-keyword-video/keywords/extract")
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "scan_required"
