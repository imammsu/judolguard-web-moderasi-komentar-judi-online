"""Penanganan error menjadi JSON seragam."""

from __future__ import annotations

import logging

from flask import Flask
from werkzeug.exceptions import HTTPException

from .responses import fail

logger = logging.getLogger(__name__)

_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "unprocessable_entity",
    429: "rate_limited",
    500: "internal_error",
    503: "service_unavailable",
}

_MESSAGES = {
    401: "Silakan login terlebih dahulu.",
    403: "Anda tidak memiliki akses ke sumber daya ini.",
    404: "Sumber daya tidak ditemukan.",
    405: "Metode HTTP tidak diizinkan.",
    429: "Terlalu banyak permintaan. Coba lagi beberapa saat lagi.",
    500: "Terjadi kesalahan pada server.",
}


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        status = exc.code or 500
        message = _MESSAGES.get(status) or exc.description or exc.name
        return fail(_CODES.get(status, "http_error"), message, status)

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        logger.exception("Galat tak terduga: %s", exc)
        return fail("internal_error", _MESSAGES[500], 500)
