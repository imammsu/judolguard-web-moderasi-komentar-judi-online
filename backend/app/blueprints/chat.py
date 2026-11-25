"""Endpoint chatbot analisis spam."""

from __future__ import annotations

from flask import Blueprint, current_app, g, request

from ..auth_guard import login_required
from ..extensions import limiter
from ..responses import fail, ok
from ..services.chatbot import parse_chat_request, run_chat

bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@bp.post("")
@login_required
@limiter.limit("20 per minute")
def chat():
    try:
        chat_request = parse_chat_request(request.get_json(silent=True))
    except ValueError as exc:
        return fail("invalid_request", str(exc), 400)

    result = run_chat(
        current_app._get_current_object(),
        g.owner_channel_id,
        chat_request,
    )
    return ok(
        {
            "answer": result.answer,
            "tool_used": result.tool_used,
            "provider": result.provider,
            "model": result.model,
            "fallback": result.fallback,
        }
    )
