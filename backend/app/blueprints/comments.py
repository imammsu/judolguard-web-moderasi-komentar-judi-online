"""Endpoint hasil komentar terambil dan terklasifikasi."""

from __future__ import annotations

from math import ceil

from flask import Blueprint, g, request

from ..auth_guard import login_required
from ..repositories import comment_repo, video_repo
from ..responses import fail, ok

bp = Blueprint("comments", __name__)


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
