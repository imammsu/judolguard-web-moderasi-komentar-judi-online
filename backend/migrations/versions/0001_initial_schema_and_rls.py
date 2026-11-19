"""Initial schema (8 tables) and Row Level Security (RLS) for Supabase.

Revision ID: 0001_initial_schema_and_rls
Revises: None
Create Date: 2026-11-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema_and_rls"
down_revision = None
branch_labels = None
depends_on = None

BIGINT_PK = sa.BigInteger().with_variant(sa.Integer, "sqlite")
JSONB_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
TIMESTAMPTZ = sa.DateTime(timezone=True)

ALL_TABLES = (
    "users",
    "videos",
    "comments",
    "keywords",
    "moderation_log",
    "jobs",
    "chat_logs",
    "app_meta",
)


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", BIGINT_PK, autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("channel_title", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("refresh_token_enc", sa.Text(), nullable=True),
        sa.Column("created_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", name="uq_users_channel_id"),
    )
    op.create_index("ix_users_channel_id", "users", ["channel_id"], unique=True)

    # 2. videos
    op.create_table(
        "videos",
        sa.Column("video_id", sa.Text(), nullable=False),
        sa.Column("owner_channel_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("published_at", TIMESTAMPTZ, nullable=True),
        sa.Column("comment_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_fetched_at", TIMESTAMPTZ, nullable=True),
        sa.ForeignKeyConstraint(["owner_channel_id"], ["users.channel_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("video_id"),
    )
    op.create_index("ix_videos_owner_channel_id", "videos", ["owner_channel_id"])

    # 3. comments
    op.create_table(
        "comments",
        sa.Column("comment_id", sa.Text(), nullable=False),
        sa.Column("video_id", sa.Text(), nullable=False),
        sa.Column("owner_channel_id", sa.Text(), nullable=False),
        sa.Column("author_name", sa.Text(), nullable=True),
        sa.Column("author_channel_id", sa.Text(), nullable=True),
        sa.Column("text_original", sa.Text(), nullable=False),
        sa.Column("text_prepared", sa.Text(), nullable=True),
        sa.Column("text_hash", sa.CHAR(64), nullable=True),
        sa.Column("published_at", TIMESTAMPTZ, nullable=True),
        sa.Column("like_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("zone", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("rule_hit", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("classified_at", TIMESTAMPTZ, nullable=True),
        sa.Column("user_label", sa.SmallInteger(), nullable=True),
        sa.Column("moderation_status", sa.Text(), server_default="none", nullable=False),
        sa.CheckConstraint("zone IN ('judol', 'review', 'bukan')", name="ck_comments_zone"),
        sa.CheckConstraint("user_label IN (0, 1)", name="ck_comments_user_label"),
        sa.CheckConstraint(
            "moderation_status IN ('none', 'rejected', 'failed')",
            name="ck_comments_moderation_status",
        ),
        sa.ForeignKeyConstraint(["owner_channel_id"], ["users.channel_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.video_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("comment_id"),
    )
    op.create_index(
        "ix_comments_owner_video_zone",
        "comments",
        ["owner_channel_id", "video_id", "zone"],
    )
    op.create_index("ix_comments_author_channel_id", "comments", ["author_channel_id"])
    op.create_index("ix_comments_text_hash", "comments", ["text_hash"])

    # 4. keywords
    op.create_table(
        "keywords",
        sa.Column("id", BIGINT_PK, autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Text(), nullable=False),
        sa.Column("owner_channel_id", sa.Text(), nullable=False),
        sa.Column("keyword", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("frequency", sa.Integer(), server_default="1", nullable=False),
        sa.Column("extracted_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("type IN ('situs', 'kata_kunci')", name="ck_keywords_type"),
        sa.ForeignKeyConstraint(["owner_channel_id"], ["users.channel_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.video_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "keyword", name="uq_keywords_video_keyword"),
    )
    op.create_index("ix_keywords_owner_video", "keywords", ["owner_channel_id", "video_id"])

    # 5. moderation_log
    op.create_table(
        "moderation_log",
        sa.Column("id", BIGINT_PK, autoincrement=True, nullable=False),
        sa.Column("owner_channel_id", sa.Text(), nullable=False),
        sa.Column("comment_id", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_channel_id"], ["users.channel_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderation_log_owner_channel_id", "moderation_log", ["owner_channel_id"])

    # 6. jobs
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_channel_id", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("video_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("progress", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "type IN ('scan', 'fetch', 'classify', 'extract')",
            name="ck_jobs_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'done', 'failed')",
            name="ck_jobs_status",
        ),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_jobs_progress"),
        sa.ForeignKeyConstraint(["owner_channel_id"], ["users.channel_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_owner_status", "jobs", ["owner_channel_id", "status"])

    # 7. chat_logs
    op.create_table(
        "chat_logs",
        sa.Column("id", BIGINT_PK, autoincrement=True, nullable=False),
        sa.Column("owner_channel_id", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("tool_used", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_channel_id"], ["users.channel_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_logs_owner_channel_id", "chat_logs", ["owner_channel_id"])

    # 8. app_meta
    op.create_table(
        "app_meta",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", JSONB_TYPE, nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    # 9. Aktifkan Row Level Security (RLS) tanpa policy pada semua tabel di PostgreSQL Supabase
    #    agar akses lewat kunci publik REST API ditolak (PRD 11.3 & 14.1).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in (*ALL_TABLES, "alembic_version"):
            op.execute(sa.text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;"))


def downgrade() -> None:
    for table in reversed(ALL_TABLES):
        op.drop_table(table)
