"""Endpoint chatbot analisis spam."""

from __future__ import annotations

import logging
from uuid import UUID

from flask import Blueprint, current_app, g, request

from ..auth_guard import login_required
from ..extensions import limiter
from ..repositories import chat_log_repo, chat_session_repo
from ..responses import fail, ok
from ..services.chatbot import parse_chat_request, run_chat

logger = logging.getLogger(__name__)
bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@bp.post("")
@login_required
@limiter.limit("20 per minute")
def chat():
    try:
        chat_request = parse_chat_request(request.get_json(silent=True))
    except ValueError as exc:
        return fail("invalid_request", str(exc), 400)

    session = (
        chat_session_repo.get_session(g.owner_channel_id, chat_request.session_id)
        if chat_request.session_id
        else chat_session_repo.create_session(
            g.owner_channel_id,
            chat_request.video_id,
        )
    )
    if session is None:
        return fail("session_not_found", "Sesi chatbot tidak ditemukan.", 404)

    result = run_chat(
        current_app._get_current_object(),
        g.owner_channel_id,
        chat_request,
        session,
    )
    try:
        chat_log_repo.create_chat_log(
            g.owner_channel_id,
            session_id=session.id,
            question=chat_request.question,
            tool_used=result.tool_used,
            answer=result.answer,
        )
        chat_session_repo.touch_session(session)
    except Exception:  # noqa: BLE001
        logger.exception("Gagal menyimpan chat log untuk channel %s", g.owner_channel_id)
    return ok(
        {
            "session_id": str(session.id),
            "answer": result.answer,
            "tool_used": result.tool_used,
            "provider": result.provider,
            "model": result.model,
            "fallback": result.fallback,
        }
    )


@bp.get("/history")
@login_required
def chat_history():
    limit = request.args.get("limit", "50")
    try:
        parsed_limit = max(1, min(100, int(limit)))
    except ValueError:
        parsed_limit = 50
    logs = chat_log_repo.list_chat_logs(g.owner_channel_id, parsed_limit)
    return ok(
        {
            "items": [chat_log_repo.serialize_chat_log(log) for log in reversed(logs)],
            "total": len(logs),
        }
    )


@bp.post("/sessions")
@login_required
def create_session():
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return fail("invalid_request", "Body request harus berupa object JSON.", 400)
    video_id = payload.get("video_id")
    if video_id is not None and (not isinstance(video_id, str) or len(video_id) > 100):
        return fail("invalid_request", "video_id tidak valid.", 400)
    try:
        session = chat_session_repo.create_session(g.owner_channel_id, video_id or None)
    except ValueError as exc:
        return fail("invalid_request", str(exc), 400)
    return ok(chat_session_repo.serialize_session(session), 201)


@bp.get("/sessions")
@login_required
def list_sessions():
    video_id = request.args.get("video_id")
    limit = request.args.get("limit", "50")
    try:
        parsed_limit = max(1, min(100, int(limit)))
    except ValueError:
        parsed_limit = 50
    sessions = chat_session_repo.list_sessions(
        g.owner_channel_id,
        video_id=video_id,
        limit=parsed_limit,
    )
    return ok(
        {
            "items": [chat_session_repo.serialize_session(item) for item in sessions],
            "total": len(sessions),
        }
    )


@bp.get("/sessions/<uuid:session_id>/messages")
@login_required
def session_messages(session_id: UUID):
    session = chat_session_repo.get_session(g.owner_channel_id, session_id)
    if session is None:
        return fail("session_not_found", "Sesi chatbot tidak ditemukan.", 404)
    logs = chat_log_repo.list_chat_logs(
        g.owner_channel_id,
        limit=50,
        session_id=session.id,
    )
    return ok(
        {
            "session_id": str(session.id),
            "items": [chat_log_repo.serialize_chat_log(log) for log in reversed(logs)],
            "total": len(logs),
        }
    )


@bp.delete("/sessions/<uuid:session_id>")
@login_required
def delete_session(session_id: UUID):
    if not chat_session_repo.delete_session(g.owner_channel_id, session_id):
        return fail("session_not_found", "Sesi chatbot tidak ditemukan.", 404)
    return ok({"deleted": True})
