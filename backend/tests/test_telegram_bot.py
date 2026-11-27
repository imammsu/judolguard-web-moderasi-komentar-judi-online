"""Uji bot Telegram dasar tanpa memanggil Telegram API."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.telegram.bot import build_application, run_bot
from app.telegram.commands import help_command, start_command


class _FakeMessage:
    def __init__(self) -> None:
        self.responses: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.responses.append(text)


def _run(handler, args: list[str] | None = None) -> _FakeMessage:
    message = _FakeMessage()
    update = SimpleNamespace(effective_message=message)
    context = SimpleNamespace(args=args or [])
    asyncio.run(handler(update, context))
    return message


def test_start_without_token_explains_pairing():
    message = _run(start_command)
    assert "Hubungkan Telegram" in message.responses[0]
    assert "JudolGuard Sentinel" in message.responses[0]


def test_start_with_token_does_not_pair_before_stage_three():
    message = _run(start_command, ["temporary-token"])
    assert "Pairing belum dapat diproses" in message.responses[0]


def test_help_lists_sentinel_commands():
    message = _run(help_command)
    assert "/status" in message.responses[0]
    assert "/putuskan" in message.responses[0]


def test_build_application_requires_token():
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        build_application("")


def test_build_application_registers_handlers_without_network():
    application = build_application("123456:local-test-token")
    assert len(application.handlers) == 1
    assert len(application.handlers[0]) == 12


def test_run_bot_requires_explicit_enable_flag():
    with pytest.raises(RuntimeError, match="SENTINEL_ENABLED=false"):
        run_bot({"SENTINEL_ENABLED": False, "TELEGRAM_BOT_TOKEN": "unused"})
