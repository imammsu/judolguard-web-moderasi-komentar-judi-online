"""Endpoint status background job."""

from __future__ import annotations

import uuid

from flask import Blueprint, g

from ..auth_guard import login_required
from ..repositories import job_repo
from ..responses import fail, ok

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


def _serialize_job(job) -> dict[str, object]:
    return {
        "id": str(job.id),
        "type": job.type,
        "video_id": job.video_id,
        "status": job.status,
        "progress": job.progress,
        "total": job.total,
        "processed": job.processed,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@bp.get("/<task_id>")
@login_required
def get_task(task_id: str):
    try:
        parsed_id = uuid.UUID(task_id)
    except ValueError:
        return fail("invalid_task_id", "ID tugas tidak valid.", 400)

    job = job_repo.get_job(g.owner_channel_id, parsed_id)
    if job is None:
        return fail("task_not_found", "Tugas tidak ditemukan.", 404)
    return ok(_serialize_job(job))
