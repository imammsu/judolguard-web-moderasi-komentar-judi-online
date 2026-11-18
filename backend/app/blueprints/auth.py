"""Blueprint `auth` - masih kosong pada Part 1.

Login OAuth Google/YouTube (Part 2): GET /auth/login, GET /auth/callback, POST /auth/logout, GET /api/me.
"""

from flask import Blueprint

bp = Blueprint("auth", __name__, url_prefix="/auth")
