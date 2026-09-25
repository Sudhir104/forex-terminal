import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")


@pytest.fixture
def client(session):
    from app.main import create_app
    from app.models import CurrencyScore, User
    from app.services.auth import hash_password
    from app.timeutil import utcnow

    session.add(User(email="admin@test.com", password_hash=hash_password("pw12345"), is_admin=True))
    session.add(CurrencyScore(currency="USD", computed_at=utcnow(), total=6.5, coverage=1.0, confidence="high",
                              surprise_method="vs_previous",
                              factors={"monetary": 7.0, "inflation": 6.0}, evidence={"monetary": {"notes": "up"}, "inflation": {"notes": "steady"}},
                              weights={"monetary": 0.25}))
    session.add(CurrencyScore(currency="EUR", computed_at=utcnow(), total=4.5, coverage=1.0, confidence="high",
                              surprise_method="vs_previous",
                              factors={"monetary": 4.0}, evidence={"monetary": {"notes": "cuts"}}, weights={"monetary": 0.25}))
    session.commit()

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_health_no_auth_needed(client):
    r = client.get("/api/health")
    assert r.status_code == 200


def test_protected_route_requires_auth(client):
    r = client.get("/api/currencies")
    assert r.status_code == 401


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "wrong"})
    assert r.status_code == 401


def test_login_and_fetch_currencies(client):
    r = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "pw12345"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r2 = client.get("/api/currencies", headers=headers)
    assert r2.status_code == 200
    data = {c["currency"]: c for c in r2.json()}
    assert data["USD"]["total"] == 6.5


def test_unknown_currency_404(client):
    r = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "pw12345"})
    token = r.json()["access_token"]
    r2 = client.get("/api/currencies/XYZ", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 404


def test_admin_only_route_blocked_for_non_admin(client, session):
    from app.models import User
    from app.services.auth import hash_password
    session.add(User(email="user@test.com", password_hash=hash_password("pw12345"), is_admin=False))
    session.commit()
    r = client.post("/api/auth/login", json={"email": "user@test.com", "password": "pw12345"})
    token = r.json()["access_token"]
    r2 = client.get("/api/admin/weights", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 403


def test_cron_endpoint_requires_token(client):
    r = client.post("/api/internal/tick/scores")
    assert r.status_code == 401
