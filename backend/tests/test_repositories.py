"""Uji Part 3: Skema 8 tabel, user_repo (refresh token terenkripsi Fernet), meta_repo, & CASCADE."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from app.extensions import db, oauth
from app.models import (
    AppMeta,
    ChatLog,
    Comment,
    Job,
    Keyword,
    ModerationLog,
    User,
    Video,
)
from app.repositories import meta_repo, user_repo


def test_all_eight_tables_exist_in_metadata(app):
    with app.app_context():
        expected = {
            "users",
            "videos",
            "comments",
            "keywords",
            "moderation_log",
            "jobs",
            "chat_logs",
            "app_meta",
        }
        assert expected.issubset(set(db.metadata.tables.keys()))


def test_upsert_user_encrypts_refresh_token_and_preserves_on_empty_relogin(app):
    with app.app_context():
        plain_token = "1//0g-SUPER-SECRET-REFRESH-TOKEN"
        user = user_repo.upsert_user(
            channel_id="UC_CHANNEL_001",
            email="owner@example.com",
            channel_title="Channel Satu",
            thumbnail_url="https://yt3.ggpht.com/1.jpg",
            refresh_token_plain=plain_token,
        )
        assert user.id is not None
        assert user.refresh_token_enc is not None
        # Pastikan yang tersimpan di DB bukan teks biasa (terenkripsi Fernet)
        assert user.refresh_token_enc != plain_token
        assert user.refresh_token_enc.startswith("gAAAAA")
        assert user_repo.get_decrypted_refresh_token("UC_CHANNEL_001") == plain_token

        # Login ulang tanpa refresh_token baru tidak boleh menghapus refresh_token_enc lama
        updated = user_repo.upsert_user(
            channel_id="UC_CHANNEL_001",
            email="owner_new@example.com",
            channel_title="Channel Satu Baru",
            refresh_token_plain="",
        )
        assert updated.email == "owner_new@example.com"
        assert updated.channel_title == "Channel Satu Baru"
        assert user_repo.get_decrypted_refresh_token("UC_CHANNEL_001") == plain_token


def test_oauth_callback_persists_encrypted_user_in_database(client, app, monkeypatch):
    login_res = client.get("/auth/login")
    state = parse_qs(urlparse(login_res.headers["Location"]).query)["state"][0]

    monkeypatch.setattr(
        oauth.google,
        "authorize_access_token",
        lambda: {
            "access_token": "ya29.access-db-test",
            "refresh_token": "1//refresh-db-test-secret",
            "expires_at": 1899999999,
            "userinfo": {"email": "dbuser@example.com"},
        },
    )
    monkeypatch.setattr(
        "app.blueprints.auth.fetch_my_youtube_channel",
        lambda _token: {
            "channel_id": "UC_DB_PERSIST_99",
            "channel_title": "Channel DB Persist",
            "custom_url": "@dbpersist",
            "thumbnail_url": "https://yt3.ggpht.com/db.jpg",
        },
    )

    cb_res = client.get(f"/auth/callback?code=ok&state={state}")
    assert cb_res.status_code == 302

    with app.app_context():
        row = user_repo.get_user_by_channel_id("UC_DB_PERSIST_99")
        assert row is not None
        assert row.email == "dbuser@example.com"
        assert row.channel_title == "Channel DB Persist"
        assert row.refresh_token_enc != "1//refresh-db-test-secret"
        assert user_repo.get_decrypted_refresh_token("UC_DB_PERSIST_99") == "1//refresh-db-test-secret"


def test_app_meta_repository_set_get_and_sync(app):
    with app.app_context():
        meta_repo.set_meta("daily_quota", {"date": "2026-11-19", "used": 150})
        quota = meta_repo.get_meta("daily_quota")
        assert quota == {"date": "2026-11-19", "used": 150}

        meta_repo.sync_model_meta(
            {
                "model_version": "v1.0",
                "normalizer_hash": "4a078a",
                "normalizer_match": True,
                "sklearn_version": "1.6.1",
                "thresholds": {"t_low": 0.235, "t_high": 0.5},
            }
        )
        info = meta_repo.get_meta(meta_repo.MODEL_META_KEY)
        assert info is not None
        assert info["model_version"] == "v1.0"
        assert info["sklearn_version"] == "1.6.1"


def test_entities_creation_and_delete_user(app):
    with app.app_context():
        user = user_repo.upsert_user(
            channel_id="UC_OWNER_1",
            email="u1@example.com",
            channel_title="Owner 1",
            refresh_token_plain="1//token",
        )
        video = Video(
            video_id="VID_001",
            owner_channel_id=user.channel_id,
            title="Video Uji",
            comment_count=10,
        )
        comment = Comment(
            comment_id="CMT_001",
            video_id="VID_001",
            owner_channel_id=user.channel_id,
            author_name="Spammer",
            author_channel_id="UC_SPAM_1",
            text_original="GACOR77",
            text_prepared="brandtoken",
            text_hash="a" * 64,
            zone="judol",
            score=0.98,
            rule_hit=False,
        )
        kw = Keyword(
            video_id="VID_001",
            owner_channel_id=user.channel_id,
            keyword="GACOR77",
            type="situs",
            frequency=5,
        )
        log = ModerationLog(
            owner_channel_id=user.channel_id,
            comment_id="CMT_001",
            action="reject",
            status="rejected",
        )
        job = Job(
            owner_channel_id=user.channel_id,
            type="scan",
            video_id="VID_001",
            status="done",
            progress=100,
        )
        chat = ChatLog(
            owner_channel_id=user.channel_id,
            question="Siapa spammer terbanyak?",
            tool_used="top_spammers",
            answer="Spammer (1 komentar).",
        )
        meta = AppMeta(key="test_key", value={"ok": True})
        db.session.add_all([video, comment, kw, log, job, chat, meta])
        db.session.commit()

        assert db.session.get(Video, "VID_001") is not None
        assert db.session.get(Comment, "CMT_001") is not None
        assert db.session.get(Job, job.id) is not None
        assert user_repo.delete_user_and_all_data("UC_OWNER_1") is True
        assert db.session.get(User, user.id) is None
