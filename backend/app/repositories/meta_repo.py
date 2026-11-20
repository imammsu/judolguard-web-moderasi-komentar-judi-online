"""Repository untuk tabel `app_meta` (PRD 11.1, 13.3, 14.3)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..extensions import db
from ..models import AppMeta

MODEL_META_KEY = "ml_model_info"
VIDEO_SYNC_META_PREFIX = "video_sync:"


def get_meta(key: str) -> dict[str, Any] | None:
    row = db.session.get(AppMeta, key)
    if row is None:
        return None
    return dict(row.value or {})


def set_meta(key: str, value: dict[str, Any]) -> AppMeta:
    row = db.session.get(AppMeta, key)
    if row is None:
        row = AppMeta(key=key, value=dict(value))
        db.session.add(row)
    else:
        row.value = dict(value)
    db.session.commit()
    return row


def get_video_sync_meta(owner_channel_id: str) -> dict[str, Any]:
    return get_meta(f"{VIDEO_SYNC_META_PREFIX}{owner_channel_id}") or {}


def set_video_sync_meta(owner_channel_id: str, value: dict[str, Any]) -> AppMeta:
    return set_meta(f"{VIDEO_SYNC_META_PREFIX}{owner_channel_id}", value)


def sync_model_meta(ml_status: dict[str, Any]) -> AppMeta:
    """Simpan metadata model ML yang aktif ke tabel `app_meta`."""
    payload = {
        "model_version": ml_status.get("model_version"),
        "normalizer_hash": ml_status.get("normalizer_hash"),
        "normalizer_match": ml_status.get("normalizer_match"),
        "sklearn_version": ml_status.get("sklearn_version"),
        "thresholds": ml_status.get("thresholds"),
        "loaded_at": datetime.now(UTC).isoformat(),
    }
    return set_meta(MODEL_META_KEY, payload)
