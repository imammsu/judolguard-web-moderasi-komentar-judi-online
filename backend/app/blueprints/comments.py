"""Blueprint `comments` - masih kosong pada Part 1.

Koreksi label & reject (Part 5-6): POST /api/comments/label, POST /api/comments/reject (multi-ID batch).
"""

from flask import Blueprint

bp = Blueprint("comments", __name__, url_prefix="/api/comments")
