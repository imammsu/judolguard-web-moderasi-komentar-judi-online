"""Blueprint `tasks` - masih kosong pada Part 1.

Status job latar belakang (Part 4-5): GET /api/tasks/<task_id>.
"""

from flask import Blueprint

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")
