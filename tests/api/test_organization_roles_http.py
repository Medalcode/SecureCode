"""HTTP authorization contracts for the three explicit SecureCode roles."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from securecode.adapters.postgres.models import Base, EvaluationRecord, EvidenceRecord, User
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
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "Another Organization", "username": "owner@acme.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
        }).status_code == 409
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "Acme Security", "username": "another@acme.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
        }).status_code == 409
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "Injected Role", "username": "injected@example.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "role": "platform_admin",
        }).status_code == 422
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "Weak Password", "username": "weak@example.test",
            "password": "onlylowercase12", "password_confirmation": "onlylowercase12",
        }).status_code == 422
        owner_a = _headers(client, "owner@acme.test", "OwnerPassword#2026")
        owner_b = _headers(client, "owner@beta.test", "OwnerPassword#2026")
        analyst = client.post("/api/v1/organization/members", headers=owner_a, json={
            "username": "analyst@acme.test", "password": "AnalystPassword#2026",
        })
        assert analyst.status_code == 201
        entitlement = client.get("/api/v1/organization/analyst-entitlements", headers=owner_a)
        assert entitlement.status_code == 200
        assert entitlement.json() == {
            "analyst_limit": 3, "active_analysts": 1, "analysts_remaining": 2, "source": "Pro",
        }
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

        beta_analyst = client.post("/api/v1/organization/members", headers=owner_b, json={
            "username": "analyst@beta.test", "password": "AnalystPassword#2026",
        })
        assert beta_analyst.status_code == 201

        beta_members = client.get("/api/v1/organization/members", headers=owner_b)
        assert beta_members.status_code == 200
        assert {member["username"] for member in beta_members.json()} == {"owner@beta.test", "analyst@beta.test"}

        beta_evidence = EvidenceRecord(
            id=uuid4(), control_id="GH-001", evidence_hash="b" * 64, raw_evidence={}, collected_at=datetime.now(UTC),
        )
        acme_evidence = EvidenceRecord(
            id=uuid4(), control_id="GH-001", evidence_hash="a" * 64, raw_evidence={}, collected_at=datetime.now(UTC),
        )
        session.add_all((beta_evidence, acme_evidence))
        session.add_all((
            EvaluationRecord(id=uuid4(), control_id="GH-001", rule_id="GH-001-RULE", rule_version=1, status="PASS", evaluated_at=datetime.now(UTC), evidence_id=beta_evidence.id, requested_by_user_id=UUID(beta_analyst.json()["id"]), source_type="GitHub", source_repository="beta/private", source_branch="main"),
            EvaluationRecord(id=uuid4(), control_id="GH-001", rule_id="GH-001-RULE", rule_version=1, status="PASS", evaluated_at=datetime.now(UTC), evidence_id=acme_evidence.id, requested_by_user_id=UUID(analyst.json()["id"]), source_type="GitHub", source_repository="acme/private", source_branch="main"),
        ))
        session.commit()
        beta_history = client.get("/api/v1/evaluations/history", headers=owner_b)
        assert beta_history.status_code == 200
        assert any(item["repository"] == "beta/private" for item in beta_history.json()["evaluations"])
        assert not any(item["repository"] == "acme/private" for item in beta_history.json()["evaluations"])

        platform_headers = {"Authorization": f"Bearer {create_access_token(str(platform_admin.id))}"}
        assert client.get("/api/v1/admin/users", headers=platform_headers).status_code == 200
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_pro_plan_rejects_a_fourth_active_analyst(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "Seat Limited", "username": "owner@seats.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
        }).status_code == 201
        owner_headers = _headers(client, "owner@seats.test", "OwnerPassword#2026")
        for number in range(1, 4):
            created = client.post("/api/v1/organization/members", headers=owner_headers, json={
                "username": f"analyst{number}@seats.test", "password": "AnalystPassword#2026",
            })
            assert created.status_code == 201
        rejected = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst4@seats.test", "password": "AnalystPassword#2026",
        })
        assert rejected.status_code == 409
        assert "3/3" in rejected.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()
