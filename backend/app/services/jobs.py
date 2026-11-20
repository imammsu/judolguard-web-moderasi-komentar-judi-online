"""Background worker untuk alur Scan & Klasifikasi komentar."""

from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from flask import Flask

from ..extensions import db
from ..ml import get_registry
from ..repositories import comment_repo, job_repo
from .youtube import YouTubeServiceError, fetch_video_comments

logger = logging.getLogger(__name__)
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="judolguard-job")


def _run_scan_job(
    app: Flask,
    job_id: uuid.UUID,
    owner_channel_id: str,
    video_id: str,
    access_token: str,
) -> None:
    with app.app_context():
        try:
            job_repo.update_job(job_id, status="running", progress=5)

            known_ids = comment_repo.get_comment_ids(owner_channel_id, video_id)
            fetch_result = fetch_video_comments(
                access_token,
                video_id,
                known_ids,
                max_comments=int(app.config.get("MAX_COMMENTS_PER_SCAN", 2000)),
                max_pages=int(app.config.get("MAX_COMMENT_PAGES_PER_SCAN", 20)),
            )
            comment_repo.bulk_upsert_comments(owner_channel_id, video_id, fetch_result.comments)
            job_repo.update_job(
                job_id,
                progress=50,
                total=len(fetch_result.comments),
                processed=len(fetch_result.comments),
            )

            unclassified = comment_repo.get_unclassified_comments(owner_channel_id, video_id)
            if not unclassified:
                job_repo.update_job(
                    job_id,
                    status="done",
                    progress=100,
                    total=0,
                    processed=0,
                )
                return

            job_repo.update_job(
                job_id,
                progress=60,
                total=len(unclassified),
                processed=0,
            )
            texts = [comment.text_original for comment in unclassified]
            results = get_registry().classify_array(texts)
            classifications: list[dict[str, Any]] = []
            for comment, result in zip(unclassified, results, strict=True):
                classifications.append(
                    {
                        "comment_id": comment.comment_id,
                        **result.to_dict(),
                    }
                )

            job_repo.update_job(
                job_id,
                progress=90,
                total=len(unclassified),
                processed=0,
            )
            updated = comment_repo.bulk_update_classifications(
                owner_channel_id,
                video_id,
                classifications,
            )
            job_repo.update_job(
                job_id,
                status="done",
                progress=100,
                total=len(unclassified),
                processed=updated,
            )
        except YouTubeServiceError as exc:
            logger.warning("Scan komentar gagal untuk job %s: %s", job_id, exc.message)
            db.session.rollback()
            job_repo.update_job(
                job_id,
                status="failed",
                progress=100,
                error=exc.message,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Scan komentar gagal untuk job %s", job_id)
            db.session.rollback()
            job_repo.update_job(
                job_id,
                status="failed",
                progress=100,
                error=f"{type(exc).__name__}: {exc}",
            )
        finally:
            db.session.remove()


def submit_scan_job(
    app: Flask,
    job_id: uuid.UUID,
    owner_channel_id: str,
    video_id: str,
    access_token: str,
) -> None:
    """Jalankan inline saat test, atau submit ke worker saat runtime normal."""
    if app.config.get("TESTING"):
        _run_scan_job(app, job_id, owner_channel_id, video_id, access_token)
        return
    _EXECUTOR.submit(
        _run_scan_job,
        app,
        job_id,
        owner_channel_id,
        video_id,
        access_token,
    )
