"""Endpoint web untuk pairing dan status Telegram Sentinel."""

from __future__ import annotations

from flask import Blueprint, current_app, g

from ..auth_guard import login_required
from ..extensions import limiter
from ..repositories import telegram_repo, user_repo
from ..responses import fail, ok
from ..services.telegram_pairing import (
    PairingError,
    create_pairing_link,
    mask_chat_id,
)

bp = Blueprint("telegram", __name__, url_prefix="/api/telegram")


@bp.post("/pairing")
@login_required
@limiter.limit("5 per minute")
def create_pairing():
    user = user_repo.get_user_by_channel_id(g.owner_channel_id)
    if user is None:
        return fail("user_not_found", "Data pengguna belum tersedia.", 404)

    try:
        pairing = create_pairing_link(
            user.id,
            str(current_app.config.get("TELEGRAM_BOT_USERNAME") or ""),
            int(current_app.config.get("PAIRING_TOKEN_TTL_SECONDS", 600)),
        )
    except PairingError as exc:
        return fail(exc.code, exc.message, 503)

    return ok(
        {
            "pairing_url": pairing.url,
            "expires_at": pairing.expires_at.isoformat(),
            "expires_in": pairing.expires_in,
        }
    )


@bp.get("/status")
@login_required
def telegram_status():
    user = user_repo.get_user_by_channel_id(g.owner_channel_id)
    if user is None:
        return fail("user_not_found", "Data pengguna belum tersedia.", 404)

    link = telegram_repo.get_link_by_user_id(user.id)
    if link is None:
        return ok(
            {
                "connected": False,
                "paused": False,
                "chat_id_masked": None,
                "connected_at": None,
            }
        )

    return ok(
        {
            "connected": True,
            "paused": link.paused,
            "chat_id_masked": mask_chat_id(link.chat_id),
            "connected_at": link.created_at.isoformat() if link.created_at else None,
        }
    )
