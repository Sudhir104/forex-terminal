import os

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("CRON_TOKEN", "test-cron-token")

import pytest

from app import db as db_module


@pytest.fixture(autouse=True)
def _fresh_db():
    db_module.configure("sqlite://")
    db_module.init_db()
    yield


@pytest.fixture
def session():
    with db_module.session_scope() as s:
        yield s
