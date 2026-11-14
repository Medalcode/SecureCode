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
from securecode.api.security import create_access_token, hash_password


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    admin = User(
        id=uuid4(), username="admin@example.com", password_hash=hash_password("AdminPassword#2026"),
        active=True, role="platform_admin", created_at=datetime.now(timezone.utc),
    )
    session.add(admin)
    session.commit()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        yield TestClient(app), {"Authorization": f"Bearer {create_access_token(str(admin.id))}"}
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_admin_user_crud_runs_through_http_contract(admin_client):
    client, headers = admin_client
    create = client.post("/api/v1/admin/users", headers=headers, json={
        "username": "auditor.http@example.com",
        "password": "AuditorPassword#2026",
        "role": "platform_admin",
    })
    assert create.status_code == 201
    user_id = create.json()["id"]

    listing = client.get("/api/v1/admin/users", headers=headers)
    assert listing.status_code == 200
    assert any(item["id"] == user_id and item["role"] == "platform_admin" for item in listing.json())

    updated = client.patch(f"/api/v1/admin/users/{user_id}", headers=headers, json={"active": False})
    assert updated.status_code == 200
    assert updated.json()["active"] is False

    duplicate = client.post("/api/v1/admin/users", headers=headers, json={
        "username": "auditor.http@example.com", "password": "AuditorPassword#2026", "role": "platform_admin",
    })
    assert duplicate.status_code == 409


def test_admin_user_crud_enforces_jwt_and_password_policy(admin_client):
    client, headers = admin_client
    assert client.get("/api/v1/admin/users").status_code == 401

    weak = client.post("/api/v1/admin/users", headers=headers, json={
        "username": "weak@example.com", "password": "onlylowercase12", "role": "platform_admin",
    })
    assert weak.status_code == 422


def test_platform_admin_cannot_provision_customer_users_through_internal_crud(admin_client):
    client, admin_headers = admin_client
    created = client.post("/api/v1/admin/users", headers=admin_headers, json={
        "username": "customer.contract@example.com",
        "password": "AuditorPassword#2026",
        "role": "analyst",
    })
    assert created.status_code == 422


def test_organization_owner_controls_customer_finops_subscription_and_repository_scope(admin_client):
    client, _ = admin_client
    registration = client.post("/api/v1/auth/register", json={
        "organization_name": "Contract Example",
        "username": "owner.contract@example.com",
        "password": "OwnerPassword#2026",
        "password_confirmation": "OwnerPassword#2026",
    })
    assert registration.status_code == 201
    login = client.post("/api/v1/auth/token", data={
        "username": "owner.contract@example.com", "password": "OwnerPassword#2026",
    })
    assert login.status_code == 200
    owner_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    analyst = client.post("/api/v1/organization/members", headers=owner_headers, json={
        "username": "analyst.contract@example.com", "password": "AnalystPassword#2026",
    })
    assert analyst.status_code == 201
    analyst_id = analyst.json()["id"]
    analyst_headers = {"Authorization": f"Bearer {create_access_token(analyst_id)}"}

    settings = client.patch("/api/v1/settings", headers=analyst_headers, json={
        "default_repository": "Medalcode/SecureCode-Ground-Truth",
        "default_branch": "main",
        "theme": "dark",
    })
    assert settings.status_code == 200
    assert settings.json()["default_repository"] == "Medalcode/SecureCode-Ground-Truth"

    assert client.patch("/api/v1/finops", headers=analyst_headers, json={
        "budget_clp": 200, "alert_threshold_pct": 80, "alert_enabled": True,
    }).status_code == 403
    finops = client.patch("/api/v1/finops", headers=owner_headers, json={
        "budget_clp": 200, "alert_threshold_pct": 80, "alert_enabled": True,
    })
    assert finops.status_code == 200
    assert finops.json()["budget_clp"] == 200
    assert finops.json()["billing_data_state"] == "not_connected"

    subscription = client.get("/api/v1/subscription", headers=owner_headers)
    assert subscription.status_code == 200
    assert subscription.json()["billing_mode"] == "demo_non_billable"
    assert client.patch("/api/v1/subscription", headers=owner_headers, json={
        "plan_id": "premium", "confirmation": False,
    }).status_code == 422

    authorization = client.post("/api/v1/organization/repository-authorizations", headers=owner_headers, json={
        "user_id": analyst_id, "repository": "Medalcode/SecureCode-Ground-Truth",
    })
    assert authorization.status_code == 201
    assert authorization.json()["repository"] == "medalcode/securecode-ground-truth"

    revoked = client.patch(
        f"/api/v1/organization/repository-authorizations/{authorization.json()['id']}",
        headers=owner_headers,
        json={"active": False},
    )
    assert revoked.status_code == 200
    assert revoked.json()["active"] is False
