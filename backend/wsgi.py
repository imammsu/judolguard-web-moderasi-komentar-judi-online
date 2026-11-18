"""Entrypoint WSGI.

Pengembangan : python wsgi.py
Produksi     : gunicorn -w 2 -b 0.0.0.0:$PORT wsgi:app
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
    )
