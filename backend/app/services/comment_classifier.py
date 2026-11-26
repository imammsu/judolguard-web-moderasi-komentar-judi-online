"""Klasifikasi komentar pending untuk alur patrol Sentinel."""

from __future__ import annotations

from typing import Any

from ..ml import get_registry
from ..repositories import comment_repo


def _chunks[T](items: list[T], size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def classify_pending_comments(
    owner_channel_id: str,
    video_id: str,
    *,
    batch_size: int = 100,
    max_comments: int = 500,
) -> int:
    """Klasifikasikan komentar ``zone IS NULL`` dan kembalikan jumlah update."""
    if batch_size < 1 or max_comments < 1:
        return 0

    pending = comment_repo.get_unclassified_comments(owner_channel_id, video_id)
    pending = pending[:max_comments]
    updated = 0

    for batch in _chunks(pending, batch_size):
        results = get_registry().classify_array(
            [comment.text_original for comment in batch]
        )
        classifications: list[dict[str, Any]] = []
        for comment, result in zip(batch, results, strict=True):
            classifications.append(
                {
                    "comment_id": comment.comment_id,
                    **result.to_dict(),
                }
            )
        updated += comment_repo.bulk_update_classifications(
            owner_channel_id,
            video_id,
            classifications,
        )

    return updated
