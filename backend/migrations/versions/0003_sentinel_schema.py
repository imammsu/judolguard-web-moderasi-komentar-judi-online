"""Tambahkan skema JudolGuard Sentinel untuk pairing dan patroli Telegram."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_sentinel_schema"
down_revision = "0002_chat_sessions"
branch_labels = None
depends_on = None

BIGINT_PK = sa.BigInteger().with_variant(sa.Integer, "sqlite")
TIMESTAMPTZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "telegram_links",
        sa.Column("id", BIGINT_PK, autoincrement=True, nullable=False),
        sa.Column("user_id", BIGINT_PK, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("paused", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("min_alert_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "min_alert_count >= 0",
            name="ck_telegram_links_min_alert_count",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_telegram_links_user_id"),
        sa.UniqueConstraint("chat_id", name="uq_telegram_links_chat_id"),
    )
    op.create_index("ix_telegram_links_paused", "telegram_links", ["paused"])

    op.create_table(
        "pairing_tokens",
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        sa.Column("user_id", BIGINT_PK, nullable=False),
        sa.Column("expires_at", TIMESTAMPTZ, nullable=False),
        sa.Column("used_at", TIMESTAMPTZ, nullable=True),
        sa.Column("created_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index("ix_pairing_tokens_user_id", "pairing_tokens", ["user_id"])
    op.create_index("ix_pairing_tokens_expires_at", "pairing_tokens", ["expires_at"])

    op.create_table(
        "monitored_videos",
        sa.Column("id", BIGINT_PK, autoincrement=True, nullable=False),
        sa.Column("user_id", BIGINT_PK, nullable=False),
        sa.Column("video_id", sa.Text(), nullable=False),
        sa.Column("last_comment_count", sa.Integer(), nullable=True),
        sa.Column("last_checked_at", TIMESTAMPTZ, nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "last_comment_count IS NULL OR last_comment_count >= 0",
            name="ck_monitored_videos_comment_count",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.video_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "video_id",
            name="uq_monitored_videos_user_video",
        ),
    )
    op.create_index(
        "ix_monitored_videos_user_active",
        "monitored_videos",
        ["user_id", "active"],
    )
    op.create_index("ix_monitored_videos_video_id", "monitored_videos", ["video_id"])

    op.create_table(
        "patrol_runs",
        sa.Column("id", BIGINT_PK, autoincrement=True, nullable=False),
        sa.Column("user_id", BIGINT_PK, nullable=False),
        sa.Column("run_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.Column("videos_checked", sa.Integer(), server_default="0", nullable=False),
        sa.Column("est_api_units", sa.Integer(), server_default="0", nullable=False),
        sa.Column("new_comments", sa.Integer(), server_default="0", nullable=False),
        sa.Column("alerts_sent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "videos_checked >= 0",
            name="ck_patrol_runs_videos_checked",
        ),
        sa.CheckConstraint(
            "est_api_units >= 0",
            name="ck_patrol_runs_api_units",
        ),
        sa.CheckConstraint(
            "new_comments >= 0",
            name="ck_patrol_runs_new_comments",
        ),
        sa.CheckConstraint(
            "alerts_sent >= 0",
            name="ck_patrol_runs_alerts_sent",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patrol_runs_user_run_at", "patrol_runs", ["user_id", "run_at"])

    bind = op.get_bind()
    notified_column = sa.Column(
        "notified",
        sa.Boolean(),
        server_default=sa.text("false"),
        nullable=False,
    )
    notified_at_column = sa.Column("notified_at", TIMESTAMPTZ, nullable=True)
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("comments", recreate="always") as batch:
            batch.add_column(notified_column)
            batch.add_column(notified_at_column)
    else:
        op.add_column("comments", notified_column)
        op.add_column("comments", notified_at_column)
    op.create_index(
        "ix_comments_notification_lookup",
        "comments",
        ["owner_channel_id", "video_id", "zone", "notified"],
    )

    if bind.dialect.name == "postgresql":
        for table in (
            "telegram_links",
            "pairing_tokens",
            "monitored_videos",
            "patrol_runs",
        ):
            op.execute(sa.text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;"))


def downgrade() -> None:
    op.drop_index("ix_comments_notification_lookup", table_name="comments")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("comments", recreate="always") as batch:
            batch.drop_column("notified_at")
            batch.drop_column("notified")
    else:
        op.drop_column("comments", "notified_at")
        op.drop_column("comments", "notified")

    op.drop_index("ix_patrol_runs_user_run_at", table_name="patrol_runs")
    op.drop_table("patrol_runs")
    op.drop_index("ix_monitored_videos_video_id", table_name="monitored_videos")
    op.drop_index("ix_monitored_videos_user_active", table_name="monitored_videos")
    op.drop_table("monitored_videos")
    op.drop_index("ix_pairing_tokens_expires_at", table_name="pairing_tokens")
    op.drop_index("ix_pairing_tokens_user_id", table_name="pairing_tokens")
    op.drop_table("pairing_tokens")
    op.drop_index("ix_telegram_links_paused", table_name="telegram_links")
    op.drop_table("telegram_links")
