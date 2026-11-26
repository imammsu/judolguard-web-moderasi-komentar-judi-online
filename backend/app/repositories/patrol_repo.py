"""Repository pencatatan siklus patroli Sentinel."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from ..extensions import db
from ..models import PatrolRun


def create_patrol_run(
    user_id: int,
    *,
    videos_checked: int = 0,
    est_api_units: int = 0,
    new_comments: int = 0,
    alerts_sent: int = 0,
    error: str | None = None,
    run_at: datetime | None = None,
) -> PatrolRun:
    run = PatrolRun(
        user_id=user_id,
        run_at=run_at or datetime.now(UTC),
        videos_checked=max(0, int(videos_checked)),
        est_api_units=max(0, int(est_api_units)),
        new_comments=max(0, int(new_comments)),
        alerts_sent=max(0, int(alerts_sent)),
        error=error,
    )
    db.session.add(run)
    db.session.commit()
    return run


def record_notification_delivery(
    run_id: int,
    *,
    alerts_sent: int,
    error: str | None = None,
) -> None:
    run = db.session.scalar(select(PatrolRun).where(PatrolRun.id == run_id))
    if run is None:
        return
    run.alerts_sent += max(0, int(alerts_sent))
    if error:
        run.error = f"{run.error}; {error}" if run.error else error
    db.session.commit()
