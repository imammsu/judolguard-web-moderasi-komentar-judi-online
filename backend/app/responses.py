"""Format respons JSON seragam (PRD 8.7 - Kontrak API).

Sukses : {"success": true,  "data": ...}
Gagal  : {"success": false, "error": {"code": "...", "message": "..."}}
"""

from __future__ import annotations

from typing import Any

from flask import jsonify


def ok(data: Any = None, status: int = 200):
    return jsonify({"success": True, "data": data}), status


def fail(code: str, message: str, status: int = 400, details: Any = None):
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return jsonify({"success": False, "error": error}), status
