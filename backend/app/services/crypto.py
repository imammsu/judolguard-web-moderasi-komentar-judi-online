"""Utilitas enkripsi Fernet untuk refresh token OAuth (PRD 6.1, 14.1)."""

from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app, has_app_context

logger = logging.getLogger(__name__)

# Fallback key per proses hanya bila FERNET_KEY di .env belum diisi saat pengembangan.
_FALLBACK_FERNET_KEY = Fernet.generate_key().decode("utf-8")
_CONFIGURED_FERNET_KEY: str = ""


def configure_fernet(key: str | None) -> None:
    """Simpan FERNET_KEY saat application factory berjalan agar aman dipakai di worker thread."""
    global _CONFIGURED_FERNET_KEY
    _CONFIGURED_FERNET_KEY = (key or "").strip()


def _get_fernet() -> Fernet:
    raw_key = ""
    if has_app_context():
        raw_key = (current_app.config.get("FERNET_KEY") or "").strip()
        if not raw_key and current_app.config.get("ENV") == "production":
            raise RuntimeError("FERNET_KEY wajib diisi di .env untuk produksi")
    if not raw_key:
        raw_key = _CONFIGURED_FERNET_KEY or os.getenv("FERNET_KEY", "").strip() or _FALLBACK_FERNET_KEY
    return Fernet(raw_key.encode("utf-8"))


def encrypt_token(plain_text: str) -> str:
    """Enkripsi string token menjadi ciphertext base64 Fernet."""
    if not plain_text:
        return ""
    return _get_fernet().encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt_token(cipher_text: str) -> str:
    """Dekripsi ciphertext Fernet kembali ke string token asli."""
    if not cipher_text:
        return ""
    try:
        return _get_fernet().decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        logger.error("Gagal mendekripsi token OAuth (FERNET_KEY berubah atau data rusak)")
        raise ValueError("Token terenkripsi tidak valid") from exc
