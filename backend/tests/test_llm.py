"""Uji adapter Gemini/Groq dan fallback provider."""

from __future__ import annotations

from app.services.llm import (
    ExtractedItem,
    ExtractedKeyword,
    ExtractionResponse,
    GeminiClient,
    GroqClient,
    LLMExtractionResult,
    LLMProviderError,
    extract_with_fallback,
)


def _result(provider: str, model: str) -> LLMExtractionResult:
    return LLMExtractionResult(
        response=ExtractionResponse(
            items=[
                ExtractedItem(
                    source_id=1,
                    keywords=[ExtractedKeyword(keyword="GACOR77", type="situs")],
                )
            ]
        ),
        provider=provider,
        model=model,
    )


def test_gemini_parses_structured_json(monkeypatch):
    class FakeResponse:
        ok = True
        status_code = 200

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"items":[{"source_id":1,"keywords":'
                                        '[{"keyword":"GACOR77","type":"situs"}]}]}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

    monkeypatch.setattr("app.services.llm.requests.request", lambda *args, **kwargs: FakeResponse())
    result = GeminiClient("key", "gemini-3.5-flash-lite", 5, 0).extract_keywords(
        [{"source_id": 1, "text": "Daftar GACOR77"}]
    )

    assert result.provider == "gemini"
    assert result.model == "gemini-3.5-flash-lite"
    assert result.response.items[0].keywords[0].keyword == "GACOR77"


def test_groq_parses_json_object(monkeypatch):
    class FakeResponse:
        ok = True
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"items":[{"source_id":1,"keywords":'
                                '[{"keyword":"GACOR77","type":"situs"}]}]}'
                            )
                        }
                    }
                ]
            }

    monkeypatch.setattr("app.services.llm.requests.request", lambda *args, **kwargs: FakeResponse())
    result = GroqClient("key", "qwen/qwen3.8-27b", 5, 0).extract_keywords(
        [{"source_id": 1, "text": "Daftar GACOR77"}]
    )

    assert result.provider == "groq"
    assert result.response.items[0].keywords[0].type == "situs"


def test_fallback_uses_groq_when_gemini_fails(monkeypatch):
    def failed_gemini(self, items):
        raise LLMProviderError("gemini", "quota", code="llm_rate_limited")

    monkeypatch.setattr(GeminiClient, "extract_keywords", failed_gemini)
    monkeypatch.setattr(
        GroqClient,
        "extract_keywords",
        lambda self, items: _result("groq", "qwen/qwen3.8-27b"),
    )

    result = extract_with_fallback(
        [{"source_id": 1, "text": "Daftar GACOR77"}],
        provider_order=["gemini", "groq"],
        gemini_api_key="key",
        gemini_model="gemini-3.5-flash-lite",
        gemini_fallback_model="gemini-3.1-flash-lite",
        groq_api_key="key",
        groq_model="qwen/qwen3.8-27b",
        timeout=5,
        retries=0,
    )

    assert result.provider == "groq"
