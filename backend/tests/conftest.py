import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db


@pytest.fixture(scope="session")
def app():
    flask_app = create_app(TestingConfig)
    with flask_app.app_context():
        db.create_all()
    return flask_app


@pytest.fixture(autouse=True)
def _clean_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture()
def client(app):
    return app.test_client()
