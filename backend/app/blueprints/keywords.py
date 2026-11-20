"""Endpoint ekstraksi dan daftar keyword hasil analisis komentar judol."""

from __future__ import annotations

from flask import Blueprint, current_app, g

from ..auth_guard import login_required
from ..extensions import db
from ..repositories import comment_repo, job_repo, keyword_repo, video_repo
from ..responses import fail, ok
from ..services.jobs import submit_extract_job

bp = Blueprint("keywords", __name__)


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


def _serialize_keyword(keyword) -> dict[str, object]:
    return {
        "id": keyword.id,
        "video_id": keyword.video_id,
        "keyword": keyword.keyword,
        "type": keyword.type,
        "frequency": keyword.frequency,
        "extracted_at": keyword.extracted_at.isoformat() if keyword.extracted_at else None,
    }


@bp.post("/api/videos/<video_id>/keywords/extract")
@login_required
def extract_keywords(video_id: str):
    video = video_repo.get_video(g.owner_channel_id, video_id)
    if video is None:
        return fail("video_not_found", "Video tidak ditemukan.", 404)

    active = job_repo.get_active_job(g.owner_channel_id, video_id, "extract")
    if active is not None:
        return ok(_serialize_job(active), 202)

    latest_scan = job_repo.get_latest_job(g.owner_channel_id, video_id, "scan")
    if latest_scan is None:
        return fail(
            "scan_required",
            "Lakukan Scan & Klasifikasi terlebih dahulu.",
            409,
        )
    if latest_scan.status != "done":
        return fail(
            "scan_not_ready",
            "Scan komentar belum selesai.",
            409,
            {"scan_status": latest_scan.status},
        )

    if not comment_repo.get_extractable_judol_comments(g.owner_channel_id, video_id):
        return fail(
            "no_judol_comments",
            "Tidak ada komentar zona judol yang siap dianalisis.",
            409,
        )

    job = job_repo.create_job(g.owner_channel_id, video_id, "extract")
    submit_extract_job(
        current_app._get_current_object(),
        job.id,
        g.owner_channel_id,
        video_id,
    )
    if current_app.config.get("TESTING"):
        db.session.expire_all()
        job = job_repo.get_job(g.owner_channel_id, job.id) or job
    return ok(_serialize_job(job), 202)


@bp.get("/api/videos/<video_id>/keywords")
@login_required
def list_video_keywords(video_id: str):
    if video_repo.get_video(g.owner_channel_id, video_id) is None:
        return fail("video_not_found", "Video tidak ditemukan.", 404)
    keywords = keyword_repo.list_keywords(g.owner_channel_id, video_id)
    return ok(
        {
            "items": [_serialize_keyword(keyword) for keyword in keywords],
            "video_id": video_id,
            "total": len(keywords),
        }
    )
