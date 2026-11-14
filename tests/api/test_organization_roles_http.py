"""HTTP authorization contracts for the three explicit SecureCode roles."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from securecode.adapters.postgres.models import Base, User
from securecode.api.app import app
from securecode.api.dependencies import get_db_session
from securecode.api.security import create_access_token, hash_password


def _headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_roles_enforce_platform_and_organization_boundaries(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    platform_admin = User(
        id=uuid4(), username="platform@example.com", password_hash=hash_password("PlatformPassword#2026"),
        active=True, role="platform_admin", created_at=datetime.now(UTC),
    )
    session.add(platform_admin)
    session.commit()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        first = client.post("/api/v1/auth/register", json={
            "organization_name": "Acme Security", "username": "owner@acme.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
        })
        second = client.post("/api/v1/auth/register", json={
            "organization_name": "Beta Security", "username": "owner@beta.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
        })
        assert first.status_code == second.status_code == 201
        owner_a = _headers(client, "owner@acme.test", "OwnerPassword#2026")
        owner_b = _headers(client, "owner@beta.test", "OwnerPassword#2026")
        analyst = client.post("/api/v1/organization/members", headers=owner_a, json={
            "username": "analyst@acme.test", "password": "AnalystPassword#2026",
        })
        assert analyst.status_code == 201
        analyst_headers = _headers(client, "analyst@acme.test", "AnalystPassword#2026")

        assert client.get("/api/v1/admin/users", headers=owner_a).status_code == 403
        assert client.get("/api/v1/organization/members", headers=analyst_headers).status_code == 403
        assert client.get("/api/v1/finops", headers=analyst_headers).status_code == 403

        reset = client.patch(f"/api/v1/organization/members/{analyst.json()['id']}", headers=owner_a, json={
            "password": "RenewedPassword#2026",
        })
        assert reset.status_code == 200
        _headers(client, "analyst@acme.test", "RenewedPassword#2026")

        cross_tenant = client.post("/api/v1/organization/repository-authorizations", headers=owner_b, json={
            "user_id": analyst.json()["id"], "repository": "Acme/Sensitive",
        })
        assert cross_tenant.status_code == 404

        platform_headers = {"Authorization": f"Bearer {create_access_token(str(platform_admin.id))}"}
        assert client.get("/api/v1/admin/users", headers=platform_headers).status_code == 200
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()
