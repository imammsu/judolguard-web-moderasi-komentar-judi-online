"""Repository log moderasi dan status reject komentar."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..extensions import db
from ..models import ModerationLog


def create_logs(owner_channel_id: str, logs: list[dict[str, Any]]) -> int:
    if not logs:
        return 0
    rows = [
        ModerationLog(
            owner_channel_id=owner_channel_id,
            comment_id=str(log["comment_id"]),
            action=str(log.get("action") or "reject"),
            status=str(log["status"]),
            error=log.get("error"),
            created_at=datetime.now(UTC),
        )
        for log in logs
    ]
    db.session.add_all(rows)
    db.session.commit()
    return len(rows)
