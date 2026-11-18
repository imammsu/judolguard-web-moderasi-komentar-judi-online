"""Blueprint `keywords` - masih kosong pada Part 1.

Ekstraksi kata kunci (Part 7): POST /api/videos/<id>/keywords/extract, GET /api/videos/<id>/keywords.
"""

from flask import Blueprint

bp = Blueprint("keywords", __name__, url_prefix="/api/keywords")
