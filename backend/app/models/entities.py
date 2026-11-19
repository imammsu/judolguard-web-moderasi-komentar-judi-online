"""Model SQLAlchemy untuk seluruh 8 tabel JudolGuard (PRD Bagian 11.1 & 11.2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db

# BIGSERIAL di PostgreSQL, INTEGER AUTOINCREMENT di SQLite (untuk pytest).
BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")
JSONB_TYPE = JSON().with_variant(JSONB, "postgresql")
TIMESTAMPTZ = DateTime(timezone=True)


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(db.Model):
    """Tabel `users` — pemilik channel YouTube yang login via OAuth."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


class Video(db.Model):
    """Tabel `videos` — cache daftar video channel milik pengguna."""

    __tablename__ = "videos"

    video_id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner_channel_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.channel_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_fetched_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)


class Comment(db.Model):
    """Tabel `comments` — komentar utama video beserta hasil klasifikasi & status moderasi."""

    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint("zone IN ('judol', 'review', 'bukan')", name="ck_comments_zone"),
        CheckConstraint("user_label IN (0, 1)", name="ck_comments_user_label"),
        CheckConstraint(
            "moderation_status IN ('none', 'rejected', 'failed')",
            name="ck_comments_moderation_status",
        ),
        Index("ix_comments_owner_video_zone", "owner_channel_id", "video_id", "zone"),
        Index("ix_comments_author_channel_id", "author_channel_id"),
        Index("ix_comments_text_hash", "text_hash"),
    )

    comment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    video_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("videos.video_id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_channel_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.channel_id", ondelete="CASCADE"),
        nullable=False,
    )
    author_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_channel_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_original: Mapped[str] = mapped_column(Text, nullable=False)
    text_prepared: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Hasil klasifikasi (NULL bila belum diklasifikasi)
    zone: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rule_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    classified_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

    # Koreksi pengguna & status moderasi
    user_label: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    moderation_status: Mapped[str] = mapped_column(Text, nullable=False, default="none")


class Keyword(db.Model):
    """Tabel `keywords` — nama situs & kata kunci judol hasil ekstraksi LLM."""

    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("video_id", "keyword", name="uq_keywords_video_keyword"),
        CheckConstraint("type IN ('situs', 'kata_kunci')", name="ck_keywords_type"),
        Index("ix_keywords_owner_video", "owner_channel_id", "video_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("videos.video_id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_channel_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.channel_id", ondelete="CASCADE"),
        nullable=False,
    )
    keyword: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    extracted_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, default=utc_now, server_default=func.now()
    )


class ModerationLog(db.Model):
    """Tabel `moderation_log` — riwayat aksi reject komentar ke YouTube API."""

    __tablename__ = "moderation_log"
    __table_args__ = (Index("ix_moderation_log_owner_channel_id", "owner_channel_id"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    owner_channel_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.channel_id", ondelete="CASCADE"),
        nullable=False,
    )
    comment_id: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, default=utc_now, server_default=func.now()
    )


class Job(db.Model):
    """Tabel `jobs` — pelacak background task (scan, fetch, classify, extract)."""

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "type IN ('scan', 'fetch', 'classify', 'extract')",
            name="ck_jobs_type",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'done', 'failed')",
            name="ck_jobs_status",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_jobs_progress"),
        Index("ix_jobs_owner_status", "owner_channel_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_channel_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.channel_id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    video_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


class ChatLog(db.Model):
    """Tabel `chat_logs` — riwayat tanya-jawab chatbot analisis spam."""

    __tablename__ = "chat_logs"
    __table_args__ = (Index("ix_chat_logs_owner_channel_id", "owner_channel_id"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    owner_channel_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.channel_id", ondelete="CASCADE"),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    tool_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, default=utc_now, server_default=func.now()
    )


class AppMeta(db.Model):
    """Tabel `app_meta` — metadata aplikasi (model_version, normalizer_hash, kuota harian)."""

    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB_TYPE, nullable=False, default=dict)
