"""Uji klasifikasi batch komentar untuk Sentinel."""

from __future__ import annotations

from app.extensions import db
from app.ml.loader import ClassificationResult
from app.models import Comment, Video
from app.repositories import user_repo
from app.services.comment_classifier import classify_pending_comments


def _seed_pending_comments(app) -> str:
    with app.app_context():
        user = user_repo.upsert_user(
            channel_id="UC_CLASSIFIER_OWNER",
            email="classifier@example.com",
            refresh_token_plain="refresh-token",
        )
        db.session.add(
            Video(
                video_id="video-classifier",
                owner_channel_id=user.channel_id,
                title="Video klasifikasi",
                comment_count=2,
            )
        )
        db.session.add_all(
            [
                Comment(
                    comment_id="comment-classifier-1",
                    video_id="video-classifier",
                    owner_channel_id=user.channel_id,
                    text_original="info link gacor",
                    moderation_status="none",
                    notified=False,
                ),
                Comment(
                    comment_id="comment-classifier-2",
                    video_id="video-classifier",
                    owner_channel_id=user.channel_id,
                    text_original="videonya bagus",
                    moderation_status="none",
                    notified=False,
                ),
                Comment(
                    comment_id="comment-already-classified",
                    video_id="video-classifier",
                    owner_channel_id=user.channel_id,
                    text_original="sudah diproses",
                    zone="bukan",
                    score=0.01,
                    model_version="old-model",
                    moderation_status="none",
                    notified=False,
                ),
            ]
        )
        db.session.commit()
        return user.channel_id


def test_classify_pending_comments_updates_ml_fields_in_batches(app, monkeypatch):
    owner_channel_id = _seed_pending_comments(app)
    calls: list[list[str]] = []

    class FakeRegistry:
        def classify_array(self, texts):
            calls.append(texts)
            return [
                ClassificationResult(
                    text_prepared=texts[0].lower(),
                    text_hash="a" * 64,
                    score=0.95,
                    zone="judol",
                    rule_hit=True,
                    model_version="test-model",
                )
            ]

    monkeypatch.setattr(
        "app.services.comment_classifier.get_registry",
        lambda: FakeRegistry(),
    )

    updated = classify_pending_comments(
        owner_channel_id,
        "video-classifier",
        batch_size=1,
        max_comments=2,
    )

    assert updated == 2
    assert calls == [["info link gacor"], ["videonya bagus"]]
    with app.app_context():
        comments = db.session.query(Comment).order_by(Comment.comment_id).all()
        pending = [comment for comment in comments if comment.zone is None]
        assert pending == []
        classified = db.session.get(Comment, "comment-classifier-1")
        assert classified.zone == "judol"
        assert classified.score == 0.95
        assert classified.rule_hit is True
        assert classified.model_version == "test-model"
        assert classified.text_hash == "a" * 64
        assert classified.classified_at is not None
        assert classified.notified is False

        existing = db.session.get(Comment, "comment-already-classified")
        assert existing.model_version == "old-model"


def test_classify_pending_comments_keeps_pending_when_model_fails(app, monkeypatch):
    owner_channel_id = _seed_pending_comments(app)

    class BrokenRegistry:
        def classify_array(self, texts):
            raise RuntimeError("model unavailable")

    monkeypatch.setattr(
        "app.services.comment_classifier.get_registry",
        lambda: BrokenRegistry(),
    )

    try:
        classify_pending_comments(
            owner_channel_id,
            "video-classifier",
            batch_size=2,
            max_comments=2,
        )
    except RuntimeError as error:
        assert str(error) == "model unavailable"
    else:
        raise AssertionError("Kegagalan model harus diteruskan ke caller")

    with app.app_context():
        pending_count = (
            db.session.query(Comment)
            .filter(
                Comment.video_id == "video-classifier",
                Comment.zone.is_(None),
            )
            .count()
        )
        assert pending_count == 2
