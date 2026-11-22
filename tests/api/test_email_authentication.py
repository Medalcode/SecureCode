"""End-to-end HTTP contracts for email verification and account recovery."""

import importlib
import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from securecode.adapters.postgres.models import Base, User
from securecode.api.dependencies import get_db_session
from securecode.api.security import hash_password
from securecode.api.service_documents import current_onboarding_package


def _client(monkeypatch):
    api_module = importlib.import_module("securecode.api.app")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    api_module.app.dependency_overrides[get_db_session] = lambda: session
    monkeypatch.setenv("EMAIL_VERIFICATION_REQUIRED", "true")
    monkeypatch.setenv("PUBLIC_APP_URL", "https://securecode.example.test")
    sent: list[dict[str, str]] = []

    def fake_delivery(**message):
        sent.append(message)

    monkeypatch.setattr(api_module, "send_resend_email", fake_delivery)
    return TestClient(api_module.app), session, sent


def _token(message: dict[str, str], fragment: str) -> str:
    match = re.search(rf"#{fragment}=([^\"\s<]+)", message["html"])
    assert match, message["html"]
    return match.group(1)


def test_registration_requires_email_confirmation_before_login(monkeypatch):
    client, session, sent = _client(monkeypatch)
    package = current_onboarding_package()
    response = client.post("/api/v1/auth/register", json={
        "organization_name": "Correo QA", "username": "owner@correo.test",
        "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
        "accepted_document_package_id": package.package_id,
        "accepted_document_package_version": package.version,
        "accepted_document_package_sha256": package.sha256,
        "acceptance_confirmed": True,
    })
    assert response.status_code == 201
    assert response.json()["verification_required"] is True
    assert response.json()["active"] is False
    assert len(sent) == 1
    assert client.post("/api/v1/auth/token", data={"username": "owner@correo.test", "password": "OwnerPassword#2026"}).status_code == 401

    resent = client.post("/api/v1/auth/email-verification/resend", json={"username": "owner@correo.test"})
    assert resent.status_code == 202
    assert len(sent) == 2
    assert client.post(
        "/api/v1/auth/email-verification/confirm", json={"token": _token(sent[0], "verify_email")}
    ).status_code == 400

    verified = client.post("/api/v1/auth/email-verification/confirm", json={"token": _token(sent[1], "verify_email")})
    assert verified.status_code == 200
    assert client.post("/api/v1/auth/token", data={"username": "owner@correo.test", "password": "OwnerPassword#2026"}).status_code == 200
    assert session.query(User).filter_by(username="owner@correo.test").one().email_verified_at is not None


def test_registration_and_recovery_reject_malformed_email_addresses(monkeypatch):
    client, _session, _sent = _client(monkeypatch)
    package = current_onboarding_package()
    invalid_registration = client.post("/api/v1/auth/register", json={
        "organization_name": "Correo QA", "username": "esto-no-es-correo",
        "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
        "accepted_document_package_id": package.package_id,
        "accepted_document_package_version": package.version,
        "accepted_document_package_sha256": package.sha256,
        "acceptance_confirmed": True,
    })
    invalid_recovery = client.post("/api/v1/auth/password-recovery", json={"username": "sin-arroba"})
    assert invalid_registration.status_code == 422
    assert invalid_recovery.status_code == 422


def test_password_recovery_uses_single_use_link_without_enumerating_accounts(monkeypatch):
    client, session, sent = _client(monkeypatch)
    user = User(
        id=uuid4(), username="recover@correo.test", password_hash=hash_password("OldPassword#2026"),
        active=True, role="analyst", email_verified_at=datetime.now(UTC),
    )
    session.add(user)
    session.commit()
    unknown = client.post("/api/v1/auth/password-recovery", json={"username": "unknown@correo.test"})
    requested = client.post("/api/v1/auth/password-recovery", json={"username": "recover@correo.test"})
    assert unknown.status_code == requested.status_code == 202
    assert len(sent) == 1
    token = _token(sent[0], "reset_password")
    changed = client.post("/api/v1/auth/password-recovery/confirm", json={
        "token": token, "password": "RenewedPassword#2026", "password_confirmation": "RenewedPassword#2026",
    })
    assert changed.status_code == 200
    assert client.post("/api/v1/auth/token", data={"username": "recover@correo.test", "password": "OldPassword#2026"}).status_code == 401
    assert client.post("/api/v1/auth/token", data={"username": "recover@correo.test", "password": "RenewedPassword#2026"}).status_code == 200
    assert client.post("/api/v1/auth/password-recovery/confirm", json={
        "token": token, "password": "AnotherPassword#2026", "password_confirmation": "AnotherPassword#2026",
    }).status_code == 400


def test_password_recovery_revokes_all_existing_sessions_and_preserves_others(monkeypatch):
    client, session, sent = _client(monkeypatch)
    from securecode.adapters.postgres.models import UserSession

    now = datetime.now(UTC)
    user = User(id=uuid4(), username="recover@correo.test", password_hash=hash_password("OldPassword#2026"), active=True, role="analyst", email_verified_at=now)
    other = User(id=uuid4(), username="other@correo.test", password_hash=hash_password("OtherPassword#2026"), active=True, role="analyst", email_verified_at=now)
    session.add_all([user, other])
    session.commit()

    bearer = client.post("/api/v1/auth/token", data={"username": "recover@correo.test", "password": "OldPassword#2026"}).json()["access_token"]
    browser = client.post(
        "/api/v1/auth/session",
        data={"username": "recover@correo.test", "password": "OldPassword#2026"},
        headers={"Origin": "http://testserver"},
    )
    assert browser.status_code == 200
    csrf = browser.json()["csrf_token"]
    other_bearer = client.post("/api/v1/auth/token", data={"username": "other@correo.test", "password": "OtherPassword#2026"}).json()["access_token"]

    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bearer}"}).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {other_bearer}"}).status_code == 200

    client.post("/api/v1/auth/password-recovery", json={"username": "recover@correo.test"})
    token = _token(sent[-1], "reset_password")
    changed = client.post(
        "/api/v1/auth/password-recovery/confirm",
        json={"token": token, "password": "RenewedPassword#2026", "password_confirmation": "RenewedPassword#2026"},
    )
    assert changed.status_code == 200

    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bearer}"}).status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/logout", headers={"Origin": "http://testserver", "X-CSRF-Token": csrf}).status_code == 401
    assert client.post("/api/v1/auth/token", data={"username": "recover@correo.test", "password": "OldPassword#2026"}).status_code == 401
    new_bearer = client.post("/api/v1/auth/token", data={"username": "recover@correo.test", "password": "RenewedPassword#2026"}).json()["access_token"]
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_bearer}"}).status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {other_bearer}"}).status_code == 200

    revoked = session.query(UserSession).filter(UserSession.user_id == user.id).order_by(UserSession.created_at.asc()).all()
    assert len(revoked) >= 3
    assert all(row.revoked_at is not None for row in revoked[:-1])
    assert revoked[-1].revoked_at is None
    assert session.query(UserSession).filter(UserSession.user_id == other.id, UserSession.revoked_at.is_(None)).count() >= 1

    reused = client.post(
        "/api/v1/auth/password-recovery/confirm",
        json={"token": token, "password": "AnotherPassword#2026", "password_confirmation": "AnotherPassword#2026"},
    )
    assert reused.status_code == 400


def test_password_recovery_rejects_invalid_and_expired_tokens_without_side_effects(monkeypatch):
    client, session, _sent = _client(monkeypatch)
    import hashlib
    from datetime import timedelta

    from securecode.adapters.postgres.models import AccountActionToken, UserSession

    now = datetime.now(UTC)
    user = User(id=uuid4(), username="recover@correo.test", password_hash=hash_password("OldPassword#2026"), active=True, role="analyst", email_verified_at=now)
    session.add(user)
    session.commit()
    bearer = client.post("/api/v1/auth/token", data={"username": "recover@correo.test", "password": "OldPassword#2026"}).json()["access_token"]

    invalid = client.post(
        "/api/v1/auth/password-recovery/confirm",
        json={"token": "x" * 48, "password": "RenewedPassword#2026", "password_confirmation": "RenewedPassword#2026"},
    )
    assert invalid.status_code == 400
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bearer}"}).status_code == 200
    assert client.post("/api/v1/auth/token", data={"username": "recover@correo.test", "password": "OldPassword#2026"}).status_code == 200

    raw = "expired-token-" + "a" * 40
    session.add(AccountActionToken(
        id=uuid4(), user_id=user.id, purpose="password_recovery",
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_at=now - timedelta(minutes=1), used_at=None, created_at=now - timedelta(minutes=40),
    ))
    session.commit()
    expired = client.post(
        "/api/v1/auth/password-recovery/confirm",
        json={"token": raw, "password": "RenewedPassword#2026", "password_confirmation": "RenewedPassword#2026"},
    )
    assert expired.status_code == 400
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bearer}"}).status_code == 200
    assert client.post("/api/v1/auth/token", data={"username": "recover@correo.test", "password": "OldPassword#2026"}).status_code == 200
    assert session.query(UserSession).filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)).count() >= 1


def test_password_recovery_is_atomic_when_session_revocation_fails(monkeypatch):
    client, session, sent = _client(monkeypatch)
    from securecode.api import app as api_app
    from securecode.api.security import verify_password

    now = datetime.now(UTC)
    user = User(id=uuid4(), username="recover@correo.test", password_hash=hash_password("OldPassword#2026"), active=True, role="analyst", email_verified_at=now)
    session.add(user)
    session.commit()
    bearer = client.post("/api/v1/auth/token", data={"username": "recover@correo.test", "password": "OldPassword#2026"}).json()["access_token"]
    client.post("/api/v1/auth/password-recovery", json={"username": "recover@correo.test"})
    token = _token(sent[-1], "reset_password")

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(api_app, "_revoke_user_sessions", boom)
    with TestClient(api_app.app, raise_server_exceptions=False) as failing_client:
        failing_client.cookies.update(client.cookies)
        result = failing_client.post(
            "/api/v1/auth/password-recovery/confirm",
            json={"token": token, "password": "RenewedPassword#2026", "password_confirmation": "RenewedPassword#2026"},
        )
    assert result.status_code == 500
    session.rollback()

    fresh = sessionmaker(bind=session.get_bind())()
    try:
        db_user = fresh.query(User).filter(User.username == "recover@correo.test").one()
        assert verify_password("OldPassword#2026", db_user.password_hash)
        assert not verify_password("RenewedPassword#2026", db_user.password_hash)
    finally:
        fresh.close()
    assert client.post("/api/v1/auth/token", data={"username": "recover@correo.test", "password": "OldPassword#2026"}).status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bearer}"}).status_code == 200
