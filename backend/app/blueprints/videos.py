"""Blueprint `videos` - masih kosong pada Part 1.

Daftar video & Scan (Part 4-5): GET /api/videos, POST /api/videos/<id>/scan, GET /api/videos/<id>/comments.
"""

from flask import Blueprint

bp = Blueprint("videos", __name__, url_prefix="/api/videos")
