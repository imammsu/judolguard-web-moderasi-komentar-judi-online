"""Orkestrasi ekstraksi keyword dari komentar zona judol."""

from __future__ import annotations

import re
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from flask import Flask

from ..repositories import comment_repo, keyword_repo
from .llm import LLMExtractionResult, extract_with_fallback

COMMON_KEYWORDS = {
    "ada",
    "bagi",
    "baru",
    "cek",
    "dapat",
    "di",
    "dan",
    "dengan",
    "info",
    "ini",
    "itu",
    "ke",
    "klik",
    "link",
    "langsung",
    "member",
    "resmi",
    "sekarang",
    "untuk",
    "yang",
}
WHITESPACE_RE = re.compile(r"\s+")


class ExtractionInputError(Exception):
    """Input ekstraksi tidak memenuhi prasyarat."""


@dataclass(frozen=True)
class SourceComment:
    source_id: int
    text: str
    multiplicity: int


def _normalized_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def _prepare_sources(comments) -> list[SourceComment]:
    grouped: OrderedDict[str, int] = OrderedDict()
    for comment in comments:
        text = _normalized_text(str(comment.text_original or ""))
        if text:
            grouped[text] = grouped.get(text, 0) + 1
    return [
        SourceComment(index, text, multiplicity)
        for index, (text, multiplicity) in enumerate(grouped.items(), start=1)
    ]


def _prompt_items(sources: list[SourceComment], max_chars: int) -> list[dict[str, object]]:
    return [
        {
            "source_id": source.source_id,
            "text": source.text[:max_chars],
        }
        for source in sources
    ]


def _clean_keyword(value: str) -> str:
    return WHITESPACE_RE.sub(" ", str(value or "")).strip(" \t\r\n.,;:!?()[]{}\"'")


def _aggregate_keywords(
    result: LLMExtractionResult,
    sources: list[SourceComment],
) -> list[dict[str, object]]:
    source_by_id = {source.source_id: source for source in sources}
    aggregated: OrderedDict[str, dict[str, object]] = OrderedDict()
    seen_per_source: dict[int, set[str]] = {}

    for item in result.response.items:
        source = source_by_id.get(item.source_id)
        if source is None:
            continue
        source_seen = seen_per_source.setdefault(source.source_id, set())
        source_text = source.text.casefold()
        for extracted in item.keywords:
            keyword = _clean_keyword(extracted.keyword)
            normalized = keyword.casefold()
            if (
                not keyword
                or len(keyword) > 100
                or normalized in COMMON_KEYWORDS
                or normalized in source_seen
                or normalized not in source_text
            ):
                continue
            source_seen.add(normalized)
            current = aggregated.get(normalized)
            if current is None:
                aggregated[normalized] = {
                    "keyword": keyword,
                    "type": extracted.type,
                    "frequency": source.multiplicity,
                }
            else:
                current["frequency"] = int(current["frequency"]) + source.multiplicity
                if extracted.type == "situs":
                    current["type"] = "situs"

    return sorted(
        aggregated.values(),
        key=lambda item: (-int(item["frequency"]), str(item["keyword"]).casefold()),
    )


def extract_keywords_for_video(
    app: Flask,
    owner_channel_id: str,
    video_id: str,
    *,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict[str, object]:
    comments = comment_repo.get_extractable_judol_comments(owner_channel_id, video_id)
    sources = _prepare_sources(comments)
    if not sources:
        raise ExtractionInputError("Tidak ada komentar judol yang siap diekstrak.")

    batch_size = min(
        max(1, int(app.config.get("LLM_EXTRACTION_BATCH_SIZE", 30))),
        int(app.config.get("LLM_EXTRACTION_MAX_BATCH_SIZE", 50)),
    )
    max_chars = max(100, int(app.config.get("LLM_MAX_COMMENT_CHARS", 1000)))
    batches = [
        sources[start : start + batch_size]
        for start in range(0, len(sources), batch_size)
    ]
    all_rows: list[dict[str, object]] = []
    providers: list[str] = []
    models: list[str] = []

    for index, batch in enumerate(batches, start=1):
        result = extract_with_fallback(
            _prompt_items(batch, max_chars),
            provider_order=list(app.config.get("LLM_PROVIDER_ORDER", ["gemini", "groq"])),
            gemini_api_key=str(app.config.get("GEMINI_API_KEY") or ""),
            gemini_model=str(app.config.get("GEMINI_MODEL") or ""),
            gemini_fallback_model=str(app.config.get("GEMINI_FALLBACK_MODEL") or ""),
            groq_api_key=str(app.config.get("GROQ_API_KEY") or ""),
            groq_model=str(app.config.get("GROQ_MODEL") or ""),
            timeout=max(1, int(app.config.get("LLM_REQUEST_TIMEOUT", 45))),
            retries=max(0, int(app.config.get("LLM_MAX_RETRIES", 1))),
        )
        all_rows.extend(_aggregate_keywords(result, batch))
        providers.append(result.provider)
        models.append(result.model)
        if on_progress is not None:
            on_progress(index, len(batches))

    merged: OrderedDict[str, dict[str, object]] = OrderedDict()
    for row in all_rows:
        key = str(row["keyword"]).casefold()
        current = merged.get(key)
        if current is None:
            merged[key] = dict(row)
        else:
            current["frequency"] = int(current["frequency"]) + int(row["frequency"])
            if row["type"] == "situs":
                current["type"] = "situs"

    rows = sorted(
        merged.values(),
        key=lambda item: (-int(item["frequency"]), str(item["keyword"]).casefold()),
    )
    keyword_repo.replace_keywords(owner_channel_id, video_id, rows)
    return {
        "keyword_count": len(rows),
        "source_comment_count": len(comments),
        "unique_source_count": len(sources),
        "batch_count": len(batches),
        "providers": list(dict.fromkeys(providers)),
        "models": list(dict.fromkeys(models)),
    }
