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
