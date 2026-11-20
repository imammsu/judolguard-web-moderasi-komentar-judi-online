"""Endpoint hasil komentar terambil dan terklasifikasi."""

from __future__ import annotations

from datetime import UTC, datetime
from math import ceil

from flask import Blueprint, current_app, g, request

from ..auth_guard import login_required
from ..repositories import comment_repo, meta_repo, moderation_repo, video_repo
from ..responses import fail, ok
from ..services.youtube import YouTubeServiceError, reject_comment_batch

bp = Blueprint("comments", __name__)
REJECT_BATCH_SIZE = 50
REJECT_QUOTA_UNITS = 50


def _positive_int(value: str | None, default: int, maximum: int) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, 1), maximum)


def _serialize_comment(comment) -> dict[str, object]:
    return {
        "comment_id": comment.comment_id,
        "video_id": comment.video_id,
        "author_name": comment.author_name,
        "author_channel_id": comment.author_channel_id,
        "text_original": comment.text_original,
        "published_at": comment.published_at.isoformat() if comment.published_at else None,
        "like_count": comment.like_count,
        "zone": comment.zone,
        "score": comment.score,
        "rule_hit": comment.rule_hit,
        "model_version": comment.model_version,
        "classified_at": comment.classified_at.isoformat() if comment.classified_at else None,
        "moderation_status": comment.moderation_status,
    }


def _as_bool(value: object) -> bool:
    return value is True or str(value).lower() in {"1", "true", "yes", "on"}


def _estimate_reject(comment_count: int) -> dict[str, int]:
    batch_count = ceil(comment_count / REJECT_BATCH_SIZE) if comment_count else 0
    return {
        "comment_count": comment_count,
        "batch_count": batch_count,
        "ids_per_batch": REJECT_BATCH_SIZE,
        "estimated_quota_units": batch_count * REJECT_QUOTA_UNITS,
    }


def _body() -> dict[str, object]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _resolve_targets(owner_channel_id: str, payload: dict[str, object]):
    all_judol = _as_bool(payload.get("all_judol"))
    video_id = str(payload.get("video_id") or "").strip() or None
    raw_ids = payload.get("comment_ids")

    if video_id and video_repo.get_video(owner_channel_id, video_id) is None:
        return None, fail("video_not_found", "Video tidak ditemukan.", 404)

    if all_judol:
        comments = comment_repo.get_judol_comments(owner_channel_id, video_id)
    elif isinstance(raw_ids, list):
        ids = list(dict.fromkeys(str(value).strip() for value in raw_ids if str(value).strip()))
        if not ids:
            return None, fail("no_comments_selected", "Pilih minimal satu komentar.", 400)
        comments = comment_repo.get_owned_comments_by_ids(owner_channel_id, ids)
        found_ids = {comment.comment_id for comment in comments}
        missing = [comment_id for comment_id in ids if comment_id not in found_ids]
        if missing:
            return None, fail(
                "comment_access_denied",
                "Satu atau beberapa komentar tidak ditemukan atau bukan milik Anda.",
                403,
            )
    else:
        return None, fail(
            "invalid_reject_target",
            "Kirim comment_ids atau all_judol=true.",
            400,
        )

    comments = [comment for comment in comments if comment.moderation_status != "rejected"]
    if not comments:
        return None, fail("no_pending_comments", "Tidak ada komentar yang perlu direject.", 409)
    return comments, None


def _quota_payload() -> dict[str, object]:
    date_key = datetime.now(UTC).date().isoformat()
    quota = meta_repo.get_daily_quota(
        date_key,
        int(current_app.config.get("YOUTUBE_DAILY_QUOTA_LIMIT", 10_000)),
    )
    quota["remaining_units"] = max(0, quota["daily_limit"] - quota["used_units"])
    return quota


def _serialize_moderation_summary(
    *,
    requested: int,
    rejected: list[str],
    failed: list[dict[str, str]],
    estimate: dict[str, int],
) -> dict[str, object]:
    return {
        "requested": requested,
        "succeeded": len(rejected),
        "failed": len(failed),
        **estimate,
        "rejected": rejected,
        "failures": failed,
        "quota": _quota_payload(),
    }


@bp.get("/api/videos/<video_id>/comments")
@login_required
def list_video_comments(video_id: str):
    if video_repo.get_video(g.owner_channel_id, video_id) is None:
        return fail("video_not_found", "Video tidak ditemukan.", 404)

    page = _positive_int(request.args.get("page"), 1, 10_000)
    page_size = _positive_int(request.args.get("page_size"), 50, 100)
    zone = request.args.get("zone") or None
    search = (request.args.get("search") or "").strip() or None
    sort = request.args.get("sort") or "score_desc"
    items, total = comment_repo.list_comments(
        g.owner_channel_id,
        video_id,
        zone=zone,
        search=search,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    total_pages = ceil(total / page_size) if total else 0
    if total_pages and page > total_pages:
        page = total_pages
        items, total = comment_repo.list_comments(
            g.owner_channel_id,
            video_id,
            zone=zone,
            search=search,
            sort=sort,
            page=page,
            page_size=page_size,
        )

    return ok(
        {
            "items": [_serialize_comment(comment) for comment in items],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "zone": zone,
            "search": search,
            "sort": sort,
        }
    )


@bp.post("/api/comments/reject/preview")
@login_required
def preview_reject():
    comments, error = _resolve_targets(g.owner_channel_id, _body())
    if error is not None:
        return error
    estimate = _estimate_reject(len(comments))
    quota = _quota_payload()
    estimate["remaining_quota_units"] = int(quota["remaining_units"])
    estimate["sufficient"] = int(quota["remaining_units"]) >= estimate["estimated_quota_units"]
    return ok({"estimate": estimate, "quota": quota})


@bp.post("/api/comments/reject")
@login_required
def reject_comments():
    payload = _body()
    if not _as_bool(payload.get("confirmed")):
        return fail("confirmation_required", "Konfirmasi diperlukan sebelum reject.", 400)

    comments, error = _resolve_targets(g.owner_channel_id, payload)
    if error is not None:
        return error

    comment_ids = [comment.comment_id for comment in comments]
    estimate = _estimate_reject(len(comment_ids))
    quota_before = _quota_payload()
    if int(quota_before["remaining_units"]) < estimate["estimated_quota_units"]:
        return fail(
            "quota_insufficient",
            "Estimasi kuota tidak mencukupi untuk reject komentar yang dipilih.",
            429,
            {
                "estimate": estimate,
                "quota": quota_before,
            },
        )

    rejected: list[str] = []
    failures: list[dict[str, str]] = []
    access_token = g.current_user.access_token
    batches = [
        comment_ids[start : start + REJECT_BATCH_SIZE]
        for start in range(0, len(comment_ids), REJECT_BATCH_SIZE)
    ]

    for index, batch in enumerate(batches):
        batch_logs: list[dict[str, str]] = []
        try:
            reject_comment_batch(access_token, batch)
            comment_repo.mark_moderation_status(g.owner_channel_id, batch, "rejected")
            rejected.extend(batch)
            batch_logs = [
                {"comment_id": comment_id, "status": "rejected"}
                for comment_id in batch
            ]
        except YouTubeServiceError as exc:
            batch_logs = [
                {
                    "comment_id": comment_id,
                    "status": "failed",
                    "error": exc.message,
                }
                for comment_id in batch
            ]
            comment_repo.mark_moderation_status(g.owner_channel_id, batch, "failed")
            failures.extend(
                {"comment_id": comment_id, "error": exc.message}
                for comment_id in batch
            )
            moderation_repo.create_logs(g.owner_channel_id, batch_logs)
            meta_repo.add_daily_quota_usage(
                datetime.now(UTC).date().isoformat(),
                REJECT_QUOTA_UNITS,
                int(current_app.config.get("YOUTUBE_DAILY_QUOTA_LIMIT", 10_000)),
            )
            if exc.code in {"youtube_quota_exceeded", "youtube_token_expired", "youtube_unauthorized"}:
                for pending in batches[index + 1 :]:
                    pending_error = "Batch tidak diproses setelah API menghentikan operasi."
                    comment_repo.mark_moderation_status(g.owner_channel_id, pending, "failed")
                    failures.extend(
                        {"comment_id": comment_id, "error": pending_error}
                        for comment_id in pending
                    )
                    moderation_repo.create_logs(
                        g.owner_channel_id,
                        [
                            {
                                "comment_id": comment_id,
                                "status": "failed",
                                "error": pending_error,
                            }
                            for comment_id in pending
                        ],
                    )
            continue
        moderation_repo.create_logs(g.owner_channel_id, batch_logs)
        meta_repo.add_daily_quota_usage(
            datetime.now(UTC).date().isoformat(),
            REJECT_QUOTA_UNITS,
            int(current_app.config.get("YOUTUBE_DAILY_QUOTA_LIMIT", 10_000)),
        )

    summary = _serialize_moderation_summary(
        requested=len(comment_ids),
        rejected=rejected,
        failed=failures,
        estimate=estimate,
    )
    return ok(summary, 200 if not failures else 207)
