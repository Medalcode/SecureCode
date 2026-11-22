import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from securecode.adapters.postgres.models import Base, User, UserSession
from securecode.api.app import app
from securecode.api.dependencies import get_db_session
from securecode.api.security import decode_access_token, hash_password
from tests.conftest import issue_access_token


@pytest.fixture
def session_client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    now = datetime.now(UTC)
    admin = User(
        id=uuid4(), username="admin@example.com",
        password_hash=hash_password("AdminSession#2026"),
        active=True, role="platform_admin", created_at=now,
    )
    analyst = User(
        id=uuid4(), username="analyst@example.com",
        password_hash=hash_password("AnalystSession#2026"),
        active=True, role="analyst", created_at=now,
    )
    session.add_all((admin, analyst))
    session.commit()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        yield TestClient(app), session, admin, analyst
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def _login(client, username, password):
    response = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _browser_login(client, username, password):
    return client.post(
        "/api/v1/auth/session",
        data={"username": username, "password": password},
        headers={"Origin": "http://testserver"},
    )


def test_login_creates_revocable_session(session_client):
    client, session, _, analyst = session_client
    token = _login(client, analyst.username, "AnalystSession#2026")
    payload = decode_access_token(token)
    assert payload is not None

    sessions = session.query(UserSession).filter(UserSession.user_id == analyst.id).all()
    assert len(sessions) == 1
    assert sessions[0].jti == payload.jti
    assert sessions[0].revoked_at is None
    assert client.get("/api/v1/auth/me", headers=_headers(token)).status_code == 200


def test_logout_revokes_current_session(session_client):
    client, session, _, analyst = session_client
    token = _login(client, analyst.username, "AnalystSession#2026")
    other_token = _login(client, analyst.username, "AnalystSession#2026")
    response = client.post("/api/v1/auth/logout", headers=_headers(token))
    assert response.status_code == 204
    assert client.get("/api/v1/auth/me", headers=_headers(token)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=_headers(other_token)).status_code == 200
    assert session.query(UserSession).filter(UserSession.jti == decode_access_token(token).jti).one().revoked_at is not None


def test_logout_all_revokes_every_session(session_client):
    client, _, _, analyst = session_client
    first = _login(client, analyst.username, "AnalystSession#2026")
    second = _login(client, analyst.username, "AnalystSession#2026")
    assert client.post("/api/v1/auth/logout-all", headers=_headers(first)).status_code == 204
    assert client.get("/api/v1/auth/me", headers=_headers(first)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=_headers(second)).status_code == 401


def test_password_reset_revokes_existing_sessions(session_client):
    client, session, admin, analyst = session_client
    token = _login(client, analyst.username, "AnalystSession#2026")
    admin_token = issue_access_token(session, admin.id)
    response = client.patch(
        f"/api/v1/admin/users/{analyst.id}",
        headers=_headers(admin_token),
        json={"password": "RenewedSession#2026"},
    )
    assert response.status_code == 200
    assert client.get("/api/v1/auth/me", headers=_headers(token)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=_headers(_login(client, analyst.username, "RenewedSession#2026"))).status_code == 200


def test_expired_session_is_rejected(session_client):
    client, session, _, analyst = session_client
    token = _login(client, analyst.username, "AnalystSession#2026")
    record = session.query(UserSession).one()
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert client.get("/api/v1/auth/me", headers=_headers(token)).status_code == 401


def test_token_without_jti_is_rejected(session_client):
    client, _, _, analyst = session_client
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": str(analyst.id), "iat": now, "exp": now + timedelta(minutes=60)},
        "test-secret-key-that-is-at-least-32-bytes-long",
        algorithm="HS256",
    )
    assert client.get("/api/v1/auth/me", headers=_headers(token)).status_code == 401


def test_browser_login_sets_httponly_session_and_readable_csrf_cookies(session_client):
    client, session, _, analyst = session_client
    response = _browser_login(client, analyst.username, "AnalystSession#2026")
    assert response.status_code == 200
    payload = response.json()
    assert "access_token" not in payload
    assert payload["csrf_token"]
    set_cookies = [item.lower() for item in response.headers.get_list("set-cookie")]
    assert any("securecode_session=" in item and "httponly" in item and "samesite=lax" in item for item in set_cookies)
    assert any("securecode_csrf=" in item and "httponly" not in item and "samesite=lax" in item for item in set_cookies)
    assert decode_access_token(client.cookies["securecode_session"]) is not None
    stored = session.query(UserSession).one()
    assert stored.csrf_token_hash == hashlib.sha256(payload["csrf_token"].encode()).hexdigest()
    assert client.get("/api/v1/auth/me").status_code == 200


def test_browser_session_requires_csrf_header_and_matching_origin(session_client):
    client, _, _, analyst = session_client
    login = _browser_login(client, analyst.username, "AnalystSession#2026")
    csrf_token = login.json()["csrf_token"]
    origin = {"Origin": "http://testserver"}

    assert client.post("/api/v1/auth/logout", headers=origin).status_code == 403
    assert client.post(
        "/api/v1/auth/logout",
        headers={**origin, "X-CSRF-Token": "wrong"},
    ).status_code == 403
    assert client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf_token},
    ).status_code == 403
    assert client.post(
        "/api/v1/auth/logout",
        headers={**origin, "X-CSRF-Token": csrf_token},
    ).status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_bearer_logout_does_not_require_csrf_or_origin(session_client):
    client, _, _, analyst = session_client
    token = _login(client, analyst.username, "AnalystSession#2026")
    response = client.post("/api/v1/auth/logout", headers=_headers(token))
    assert response.status_code == 204
    assert client.get("/api/v1/auth/me", headers=_headers(token)).status_code == 401


def test_browser_session_cannot_mutate_without_csrf(session_client):
    client, _, _, analyst = session_client
    _browser_login(client, analyst.username, "AnalystSession#2026")
    response = client.patch("/api/v1/settings", json={"default_repository": "owner/repo"})
    assert response.status_code == 403


def test_browser_session_accepts_https_origin_behind_trusted_proxy(session_client, monkeypatch):
    _, _, _, analyst = session_client
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "127.0.0.1/32")
    client = TestClient(app, client=("127.0.0.1", 50000))
    login = client.post(
        "/api/v1/auth/session",
        data={"username": analyst.username, "password": "AnalystSession#2026"},
        headers={"Origin": "https://securecode.example", "X-Forwarded-Proto": "https", "X-Forwarded-Host": "securecode.example"},
    )
    assert login.status_code == 200
    csrf_token = login.json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/logout",
        headers={
            "Origin": "https://securecode.example",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "securecode.example",
            "X-CSRF-Token": csrf_token,
        },
    )
    assert response.status_code == 204


def test_browser_session_rejects_untrusted_forwarded_origin(session_client, monkeypatch):
    client, _, _, analyst = session_client
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    login = client.post(
        "/api/v1/auth/session",
        data={"username": analyst.username, "password": "AnalystSession#2026"},
        headers={"Origin": "https://securecode.example", "X-Forwarded-Proto": "https", "X-Forwarded-Host": "securecode.example"},
    )
    assert login.status_code == 403
