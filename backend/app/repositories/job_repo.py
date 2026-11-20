"""Repository untuk status background job."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from ..extensions import db
from ..models import Job


def get_job(owner_channel_id: str, job_id: uuid.UUID) -> Job | None:
    stmt = select(Job).where(Job.id == job_id, Job.owner_channel_id == owner_channel_id)
    return db.session.scalars(stmt).first()


def get_active_scan(owner_channel_id: str, video_id: str) -> Job | None:
    stmt = (
        select(Job)
        .where(
            Job.owner_channel_id == owner_channel_id,
            Job.video_id == video_id,
            Job.type == "scan",
            Job.status.in_(("queued", "running")),
        )
        .order_by(Job.created_at.desc())
    )
    return db.session.scalars(stmt).first()


def get_latest_scan_statuses(
    owner_channel_id: str,
    video_ids: list[str] | set[str],
) -> dict[str, str]:
    """Ambil status scan terakhir per video tanpa query satu per satu."""
    clean_ids = list(dict.fromkeys(str(video_id) for video_id in video_ids if video_id))
    if not clean_ids:
        return {}

    statement = (
        select(Job)
        .where(
            Job.owner_channel_id == owner_channel_id,
            Job.video_id.in_(clean_ids),
            Job.type == "scan",
        )
        .order_by(Job.video_id.asc(), Job.created_at.desc())
    )
    statuses: dict[str, str] = {}
    for job in db.session.scalars(statement):
        if job.video_id and job.video_id not in statuses:
            statuses[job.video_id] = job.status
    return statuses


def create_job(owner_channel_id: str, video_id: str) -> Job:
    job = Job(
        owner_channel_id=owner_channel_id,
        type="scan",
        video_id=video_id,
        status="queued",
        progress=0,
        total=0,
        processed=0,
    )
    db.session.add(job)
    db.session.commit()
    return job


def update_job(job_id: uuid.UUID, **values: object) -> Job | None:
    job = db.session.get(Job, job_id)
    if job is None:
        return None
    for key, value in values.items():
        setattr(job, key, value)
    job.updated_at = datetime.now(UTC)
    db.session.commit()
    return job
