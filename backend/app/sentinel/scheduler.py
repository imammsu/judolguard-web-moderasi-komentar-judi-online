"""Scheduler interval sederhana untuk satu proses Sentinel worker."""

from __future__ import annotations

import logging
import threading
from asyncio import AbstractEventLoop, run_coroutine_threadsafe
from typing import Any

from flask import Flask

from ..services.telegram_notifications import (
    NotificationPlan,
    TelegramRateLimiter,
    dispatch_notifications,
)
from .patrol import run_patrol_cycle

logger = logging.getLogger(__name__)


class PatrolScheduler:
    """Menjalankan patrol cycle di thread daemon terpisah dari event loop Telegram."""

    def __init__(
        self,
        app: Flask,
        interval_seconds: int,
        *,
        bot: Any | None = None,
        event_loop: AbstractEventLoop | None = None,
    ) -> None:
        self.app = app
        self.interval_seconds = max(1, int(interval_seconds))
        self.bot = bot
        self.event_loop = event_loop
        self.rate_limiter = TelegramRateLimiter(
            int(app.config.get("TELEGRAM_MAX_MESSAGES_PER_MINUTE", 10))
        )
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="sentinel-patrol",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Scheduler Sentinel aktif dengan interval %s detik.",
            self.interval_seconds,
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=min(self.interval_seconds + 1, 10))
        self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                result = run_patrol_cycle(self.app)
                if result.notification_plans:
                    self._dispatch_notifications(result.notification_plans)
                if result.skipped_locked:
                    logger.info("Siklus patroli dilewati karena siklus sebelumnya masih berjalan.")
                else:
                    logger.info(
                        "Siklus patroli selesai; users=%s videos=%s new_comments=%s errors=%s",
                        result.users_checked,
                        result.videos_checked,
                        result.new_comments,
                        len(result.errors),
                    )
            except Exception:  # noqa: BLE001
                logger.exception("Siklus scheduler Sentinel gagal.")
            self._stop_event.wait(self.interval_seconds)

    def _dispatch_notifications(self, plans: list[NotificationPlan]) -> None:
        if self.bot is None or self.event_loop is None:
            logger.warning("Notification plan dibuat tetapi Telegram dispatcher belum tersedia.")
            return
        future = run_coroutine_threadsafe(
            dispatch_notifications(
                app=self.app,
                bot=self.bot,
                plans=plans,
                rate_limiter=self.rate_limiter,
            ),
            self.event_loop,
        )
        result = future.result()
        logger.info(
            "Notifikasi Telegram selesai; sent=%s failed=%s",
            result.sent,
            result.failed,
        )
