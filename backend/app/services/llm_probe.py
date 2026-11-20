"""Probe manual provider LLM dengan data sintetis.

Jalankan dari direktori backend:
    python -m app.services.llm_probe
"""

from __future__ import annotations

import json
import sys
from typing import Any

from ..config import Config
from .llm import GeminiClient, GroqClient, LLMProviderError

SAMPLE_ITEMS: list[dict[str, object]] = [
    {"source_id": 1, "text": "Daftar di GACOR77 untuk bonus member baru."},
    {"source_id": 2, "text": "Link BETKLIK resmi ada di bio."},
    {"source_id": 3, "text": "Komentar biasa tanpa promosi."},
]


def main() -> int:
    timeout = max(1, int(getattr(Config, "LLM_REQUEST_TIMEOUT", 45)))
    retries = max(0, int(getattr(Config, "LLM_MAX_RETRIES", 1)))
    checks: list[dict[str, Any]] = []
    clients = [
        GeminiClient(Config.GEMINI_API_KEY, Config.GEMINI_MODEL, timeout, retries),
        GeminiClient(
            Config.GEMINI_API_KEY,
            Config.GEMINI_FALLBACK_MODEL,
            timeout,
            retries,
        ),
        GroqClient(Config.GROQ_API_KEY, Config.GROQ_MODEL, timeout, retries),
    ]
    for client in clients:
        try:
            result = client.extract_keywords(SAMPLE_ITEMS)
            checks.append(
                {
                    "provider": result.provider,
                    "model": result.model,
                    "ok": True,
                    "items": len(result.response.items),
                }
            )
        except LLMProviderError as exc:
            checks.append(
                {
                    "provider": client.provider,
                    "model": client.model,
                    "ok": False,
                    "code": exc.code,
                    "message": exc.message,
                }
            )
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if any(item["ok"] for item in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
