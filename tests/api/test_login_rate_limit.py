from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from securecode.adapters.postgres.models import Base, User
from securecode.api.app import app
from securecode.api.dependencies import get_db_session
from securecode.api.security import hash_password


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LOGIN_MAX_FAILURES", "2")
    monkeypatch.setenv("LOGIN_WINDOW_SECONDS", "60")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(User(
        id=uuid4(), username="auditor@example.com", password_hash=hash_password("CorrectPassword#2026"),
        active=True, created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_login_is_locked_after_configured_failed_attempts(client):
    payload = {"username": "auditor@example.com", "password": "wrong-password"}
    assert client.post("/api/v1/auth/token", data=payload).status_code == 401
    assert client.post("/api/v1/auth/token", data=payload).status_code == 401

    response = client.post("/api/v1/auth/token", data=payload)
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


def test_successful_login_clears_previous_failures(client):
    wrong_payload = {"username": "auditor@example.com", "password": "wrong-password"}
    assert client.post("/api/v1/auth/token", data=wrong_payload).status_code == 401

    success = client.post("/api/v1/auth/token", data={"username": "auditor@example.com", "password": "CorrectPassword#2026"})
    assert success.status_code == 200
    assert client.post("/api/v1/auth/token", data=wrong_payload).status_code == 401
