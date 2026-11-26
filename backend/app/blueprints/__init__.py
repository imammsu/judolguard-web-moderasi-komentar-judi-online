"""Registrasi seluruh Blueprint."""

from flask import Flask

from . import auth, chat, comments, health, keywords, tasks, telegram, videos


def register_blueprints(app: Flask) -> None:
    for module in (health, auth, videos, comments, keywords, chat, telegram, tasks):
        app.register_blueprint(module.bp)
