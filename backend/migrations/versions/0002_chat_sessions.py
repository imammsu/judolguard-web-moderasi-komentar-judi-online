"""Tambahkan sesi chatbot dan hubungkan chat log lama ke sesi legacy."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0002_chat_sessions"
down_revision = "0001_initial_schema_and_rls"
branch_labels = None
depends_on = None

TIMESTAMPTZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_channel_id", sa.Text(), nullable=False),
        sa.Column("video_id", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_channel_id"], ["users.channel_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.video_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_sessions_owner_updated",
        "chat_sessions",
        ["owner_channel_id", "updated_at"],
    )
    op.create_index(
        "ix_chat_sessions_owner_video",
        "chat_sessions",
        ["owner_channel_id", "video_id"],
    )

    bind = op.get_bind()
    session_column = sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=True)
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("chat_logs", recreate="always") as batch:
            batch.add_column(session_column)
            batch.create_foreign_key(
                "fk_chat_logs_session_id",
                "chat_sessions",
                ["session_id"],
                ["id"],
                ondelete="CASCADE",
            )
    else:
        op.add_column("chat_logs", session_column)
        op.create_foreign_key(
            "fk_chat_logs_session_id",
            "chat_logs",
            "chat_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )
    op.create_index(
        "ix_chat_logs_session_created",
        "chat_logs",
        ["session_id", "created_at"],
    )

    owners = bind.execute(
        sa.text("SELECT DISTINCT owner_channel_id FROM chat_logs")
    ).fetchall()
    for (owner_channel_id,) in owners:
        session_id = uuid.uuid4()
        bind.execute(
            sa.text(
                """
                INSERT INTO chat_sessions
                    (id, owner_channel_id, video_id, title)
                VALUES
                    (:id, :owner_channel_id, NULL, :title)
                """
            ),
            {
                "id": str(session_id) if bind.dialect.name == "sqlite" else session_id,
                "owner_channel_id": owner_channel_id,
                "title": "Riwayat sebelumnya",
            },
        )
        bind.execute(
            sa.text(
                """
                UPDATE chat_logs
                SET session_id = :session_id
                WHERE owner_channel_id = :owner_channel_id
                """
            ),
            {
                "session_id": (
                    str(session_id) if bind.dialect.name == "sqlite" else session_id
                ),
                "owner_channel_id": owner_channel_id,
            },
        )

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text("ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;")
        )


def downgrade() -> None:
    op.drop_index("ix_chat_logs_session_created", table_name="chat_logs")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("chat_logs", recreate="always") as batch:
            batch.drop_constraint("fk_chat_logs_session_id", type_="foreignkey")
            batch.drop_column("session_id")
    else:
        op.drop_constraint("fk_chat_logs_session_id", "chat_logs", type_="foreignkey")
        op.drop_column("chat_logs", "session_id")
    op.drop_index("ix_chat_sessions_owner_video", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_owner_updated", table_name="chat_sessions")
    op.drop_table("chat_sessions")
