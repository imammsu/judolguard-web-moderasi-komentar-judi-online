"""Lapisan aturan pendamping model (PRD 9.4).

Tujuan: menangkap spam yang tidak ada di data latih, yaitu iklan tanpa brand
("info link gacor", "ketik di google", "bonus chip gratis") dan pola
kontak + ajakan (WA/Telegram/link + bonus/daftar).

Perilaku: aturan HANYA boleh menaikkan zona "bukan" menjadi "review".
Aturan tidak pernah menolak komentar secara otomatis, karena bisa menjerat
keluhan penonton yang menyebut kata-kata serupa.

Semua pola dicocokkan ke teks hasil ``prepare()`` (sudah lowercase,
URL -> ``urltoken``, nomor telepon -> ``phonetoken``, leetspeak dirapikan).
"""

from __future__ import annotations

import re

from .normalizer import prepare

# Frasa iklan judol tanpa brand eksplisit.
AD_PHRASE_RE = re.compile(
    r"\b(?:"
    r"info\s+(?:link|situs|web|room)\s+(?:gacor|slot|maxwin|jp)"
    r"|(?:ketik|cari|search)\s+(?:aja\s+)?(?:di\s+)?(?:google|gugel|gogle)"
    r"|bonus\s+(?:chip|new\s*member|deposit|depo|harian)"
    r"|chip\s+gratis"
    r"|link\s+(?:gacor|alternatif|anti\s*rungkad)"
    r"|(?:slot|situs|room)\s+gacor"
    r"|auto\s+(?:wd|maxwin|jp|jackpot|cuan)"
    r"|modal\s+receh"
    r")\b"
)

# Isyarat kontak / tautan.
CONTACT_RE = re.compile(
    r"\b(?:urltoken|phonetoken|wa|whatsapp|watsap|telegram|tele|tg|dm|link\s+(?:di\s+)?bio)\b"
)

# Kata ajakan khas judol.
CTA_RE = re.compile(
    r"\b(?:daftar|bonus|deposit|depo|wd|withdraw|jp|jackpot|gacor|maxwin|slot|togel|cuan)\b"
)


def check_rule_hit(text_original: str, text_prepared: str | None = None) -> bool:
    """Kembalikan ``True`` bila komentar cocok dengan pola iklan judol.

    ``text_prepared`` boleh diisi agar ``prepare()`` tidak dihitung dua kali.
    """
    prepared = text_prepared if text_prepared is not None else prepare(text_original)
    if not prepared:
        return False
    if AD_PHRASE_RE.search(prepared):
        return True
    return bool(CONTACT_RE.search(prepared) and CTA_RE.search(prepared))
