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
