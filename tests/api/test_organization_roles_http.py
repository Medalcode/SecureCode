import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"
"""HTTP authorization contracts for the three explicit SecureCode roles."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from securecode.adapters.postgres.models import (
    Base,
    EvaluationRecord,
    EvidenceRecord,
    User,
)
from securecode.api.app import app
from securecode.api.dependencies import get_db_session
from securecode.api.security import hash_password
from tests.conftest import issue_access_token


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
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        })
        second = client.post("/api/v1/auth/register", json={
            "organization_name": "Beta Security", "username": "owner@beta.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        })
        assert first.status_code == second.status_code == 201
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "Another Organization", "username": "owner@acme.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        }).status_code == 409
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "Acme Security", "username": "another@acme.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        }).status_code == 409
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "Injected Role", "username": "injected@example.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
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
        analyst_headers = _headers(client, "analyst@acme.test", "RenewedPassword#2026")

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

        beta_report = client.get("/api/v1/management-report", headers=owner_b)
        assert beta_report.status_code == 200
        report = beta_report.json()
        assert report["scope"] == "organization"
        assert report["organization"]["name"] == "Beta Security"
        assert report["summary"]["evaluations_all_time"] == 1
        assert report["summary"]["pass_count"] == 1
        assert report["summary"]["fail_count"] == 0
        assert report["summary"]["conformance_rate_pct"] == 100.0
        assert report["by_repository"] == [{"repository": "beta/private", "total": 1, "pass": 1, "fail": 0, "unknown": 0}]
        assert report["finops_preferences"]["billing_data_state"] == "not_connected"
        assert client.get("/api/v1/management-report", headers=analyst_headers).status_code == 403

        platform_headers = {"Authorization": f"Bearer {issue_access_token(session, platform_admin.id)}"}
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
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
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


def _temp_password_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    """Login and return headers with the temporary password displayed in the analyst response."""
    response = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_analyst_creation_with_owner_provided_password(monkeypatch):
    """Existing behavior: Owner provides a password, Analyst can login with it."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        _ = client.post("/api/v1/auth/register", json={
            "organization_name": "PasswordTestOrg", "username": "owner@password.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        })
        owner_headers = _headers(client, "owner@password.test", "OwnerPassword#2026")
        analyst = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@password.test", "password": "AnalystPassword#2026!",
        })
        assert analyst.status_code == 201
        response_data = analyst.json()
        assert response_data.get("temporary_password") is None, f"Expected no temporary_password, got: {response_data.get('temporary_password')}"
        assert response_data["username"] == "analyst@password.test"
        assert response_data["active"] is True
        assert response_data["role"] == "analyst"
        analyst_headers = _headers(client, "analyst@password.test", "AnalystPassword#2026!")
        assert client.post("/api/v1/auth/token", headers=analyst_headers, data={"username": "analyst@password.test", "password": "AnalystPassword#2026!"}).status_code == 200
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_analyst_creation_with_system_generated_temp_password(monkeypatch):
    """New functionality: System generates a temporary password, shown once to Owner."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        _ = client.post("/api/v1/auth/register", json={
            "organization_name": "TempPwdOrg", "username": "owner@temp.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        })
        owner_headers = _headers(client, "owner@temp.test", "OwnerPassword#2026")
        analyst = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@temp.test",
            "generate_temp": True,
        })
        assert analyst.status_code == 201
        response_data = analyst.json()
        # Temp password should be shown once in creation response
        temp_pwd = response_data.get("temporary_password")
        assert temp_pwd is not None, f"Expected temporary_password in response, got: {response_data}"
        assert len(temp_pwd) >= 12, f"Temp password too short: {len(temp_pwd)}"
        assert any(c.islower() for c in temp_pwd), "Temp password must have lowercase"
        assert any(c.isupper() for c in temp_pwd), "Temp password must have uppercase"
        assert any(c.isdigit() for c in temp_pwd), "Temp password must have digit"
        assert any(c in "!@#$%^&*" for c in temp_pwd), "Temp password must have symbol"
        # Analyst should be able to login with the temp password
        analyst_headers = _temp_password_headers(client, "analyst@temp.test", temp_pwd)
        assert analyst_headers is not None
        # Temp password should NOT persist in subsequent member read (value should be None)
        members = client.get("/api/v1/organization/members", headers=owner_headers)
        assert members.status_code == 200
        member = members.json()[0]
        assert member.get("temporary_password") is None, f"Temp password should not persist, got: {member.get('temporary_password')}"
        assert "analyst@temp.test" in {m["username"] for m in members.json()}
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_analyst_password_reset_with_owner_provided_password(monkeypatch):
    """Existing behavior: Owner resets Analyst password with a new provided password."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        _ = client.post("/api/v1/auth/register", json={
            "organization_name": "ResetPwdOrg", "username": "owner@reset.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        })
        owner_headers = _headers(client, "owner@reset.test", "OwnerPassword#2026")
        analyst_resp = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@reset.test", "password": "AnalystOldPassword#2026!",
        })
        assert analyst_resp.status_code == 201
        analyst_id = analyst_resp.json()["id"]
        # Reset password
        reset_resp = client.patch(f"/api/v1/organization/members/{analyst_id}", headers=owner_headers, json={
            "password": "AnalystNewPassword#2026@!",
        })
        assert reset_resp.status_code == 200
        reset_data = reset_resp.json()
        assert reset_data.get("temporary_password") is None, f"Expected None temporary_password, got: {reset_data.get('temporary_password')}"
        # Analyst should be able to login with the new password
        reset_headers = _headers(client, "analyst@reset.test", "AnalystNewPassword#2026@!")
        assert client.post("/api/v1/auth/token", headers=reset_headers, data={"username": "analyst@reset.test", "password": "AnalystNewPassword#2026@!"}).status_code == 200
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_analyst_password_reset_with_system_generated_temp_password(monkeypatch):
    """New functionality: Owner resets Analyst password, system generates temporary password."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        _ = client.post("/api/v1/auth/register", json={
            "organization_name": "ResetTempOrg", "username": "owner@resettemp.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        })
        owner_headers = _headers(client, "owner@resettemp.test", "OwnerPassword#2026")
        analyst_resp = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@resettemp.test", "password": "AnalystBasePassword#2026!",
        })
        assert analyst_resp.status_code == 201
        analyst_id = analyst_resp.json()["id"]
        # Reset password with generate_temp=true
        reset_resp = client.patch(f"/api/v1/organization/members/{analyst_id}", headers=owner_headers, json={
            "generate_temp": True,
        })
        assert reset_resp.status_code == 200
        reset_data = reset_resp.json()
        # Temp password should be shown once in reset response
        temp_pwd = reset_data.get("temporary_password")
        assert temp_pwd is not None, f"Expected temporary_password in reset response, got: {reset_data}"
        assert len(temp_pwd) >= 12, f"Temp password too short: {len(temp_pwd)}"
        # Analyst should be able to login with the temp password
        reset_headers = _temp_password_headers(client, "analyst@resettemp.test", temp_pwd)
        assert reset_headers is not None
        # Temp password should not persist in subsequent member read (value should be None)
        members = client.get("/api/v1/organization/members", headers=owner_headers)
        assert members.status_code == 200
        member = members.json()[0]
        assert member.get("temporary_password") is None, f"Temp password should not persist, got: {member.get('temporary_password')}"
        # Analyst should still be able to login with the temp password (not the old password)
        old_pwd = "AnalystBasePassword#2026!"
        login_with_old = client.post("/api/v1/auth/token", data={"username": "analyst@resettemp.test", "password": old_pwd})
        assert login_with_old.status_code == 401  # Old password should no longer work
        assert client.post("/api/v1/auth/token", headers=reset_headers, data={"username": "analyst@resettemp.test", "password": temp_pwd}).status_code == 200
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_password_not_persisted_in_subsequent_reads(monkeypatch):
    """New functionality: Temporary password must not persist in subsequent member reads."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        _ = client.post("/api/v1/auth/register", json={
            "organization_name": "PersistOrg", "username": "owner@persist.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        })
        owner_headers = _headers(client, "owner@persist.test", "OwnerPassword#2026")
        # Create analyst with system-generated temp password
        analyst_resp = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@persist.test",
            "generate_temp": True,
        })
        assert analyst_resp.status_code == 201
        temp_pwd = analyst_resp.json()["temporary_password"]
        # Verify temp password was shown
        assert temp_pwd is not None and len(temp_pwd) >= 12
        # Read members - temp password should NOT persist (value should be None)
        members = client.get("/api/v1/organization/members", headers=owner_headers)
        assert members.status_code == 200
        for member in members.json():
            assert member.get("temporary_password") is None, f"Temp password should not persist, got: {member.get('temporary_password')}"
        # Analyst should still be able to login with the temp password
        analyst_headers = _temp_password_headers(client, "analyst@persist.test", temp_pwd)
        assert client.post("/api/v1/auth/token", headers=analyst_headers, data={"username": "analyst@persist.test", "password": temp_pwd}).status_code == 200
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_analyst_creation_generate_temp_accepts_empty_password(monkeypatch):
    """generate_temp=true con password "" equivale a contraseña generada."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "EmptyPwdOrg", "username": "owner@emptypwd.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        }).status_code == 201
        owner_headers = _headers(client, "owner@emptypwd.test", "OwnerPassword#2026")
        analyst = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@emptypwd.test", "password": "", "generate_temp": True,
        })
        assert analyst.status_code == 201
        temp_pwd = analyst.json()["temporary_password"]
        assert temp_pwd is not None and len(temp_pwd) >= 12
        _temp_password_headers(client, "analyst@emptypwd.test", temp_pwd)
        members = client.get("/api/v1/organization/members", headers=owner_headers)
        assert all(member.get("temporary_password") is None for member in members.json())
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_analyst_creation_generate_temp_accepts_whitespace_password(monkeypatch):
    """generate_temp=true con password de sólo espacios equivale a generada."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "BlankPwdOrg", "username": "owner@blankpwd.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        }).status_code == 201
        owner_headers = _headers(client, "owner@blankpwd.test", "OwnerPassword#2026")
        analyst = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@blankpwd.test", "password": "   ", "generate_temp": True,
        })
        assert analyst.status_code == 201
        temp_pwd = analyst.json()["temporary_password"]
        assert temp_pwd is not None and len(temp_pwd) >= 12
        _temp_password_headers(client, "analyst@blankpwd.test", temp_pwd)
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_analyst_creation_rejects_explicit_password_with_generate_temp(monkeypatch):
    """Contraseña útil + generate_temp=true se rechaza con 422 y no crea la cuenta."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "XorCreateOrg", "username": "owner@xorcreate.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        }).status_code == 201
        owner_headers = _headers(client, "owner@xorcreate.test", "OwnerPassword#2026")
        rejected = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@xorcreate.test", "password": "AnalystPassword#2026!", "generate_temp": True,
        })
        assert rejected.status_code == 422
        members = client.get("/api/v1/organization/members", headers=owner_headers)
        assert {m["username"] for m in members.json()} == {"owner@xorcreate.test"}
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_analyst_password_reset_generate_temp_accepts_empty_and_whitespace_password(monkeypatch):
    """PATCH generate_temp=true con password "" o de espacios genera y devuelve una sola contraseña."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "BlankResetOrg", "username": "owner@blankreset.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        }).status_code == 201
        owner_headers = _headers(client, "owner@blankreset.test", "OwnerPassword#2026")
        created = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@blankreset.test", "password": "AnalystBasePassword#2026!",
        })
        assert created.status_code == 201
        analyst_id = created.json()["id"]
        first = client.patch(f"/api/v1/organization/members/{analyst_id}", headers=owner_headers, json={
            "generate_temp": True, "password": "",
        })
        assert first.status_code == 200
        temp_pwd = first.json()["temporary_password"]
        assert temp_pwd is not None and len(temp_pwd) >= 12
        assert first.json().get("temporary_password") == temp_pwd
        _temp_password_headers(client, "analyst@blankreset.test", temp_pwd)
        second = client.patch(f"/api/v1/organization/members/{analyst_id}", headers=owner_headers, json={
            "generate_temp": True, "password": "   ",
        })
        assert second.status_code == 200
        temp_pwd_two = second.json()["temporary_password"]
        assert temp_pwd_two is not None and temp_pwd_two != temp_pwd
        _temp_password_headers(client, "analyst@blankreset.test", temp_pwd_two)
        assert client.post("/api/v1/auth/token", data={
            "username": "analyst@blankreset.test", "password": temp_pwd,
        }).status_code == 401
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_analyst_password_reset_rejects_explicit_password_with_generate_temp(monkeypatch):
    """PATCH con contraseña útil + generate_temp=true se rechaza con 422 sin aplicar cambios."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "XorResetOrg", "username": "owner@xorreset.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        }).status_code == 201
        owner_headers = _headers(client, "owner@xorreset.test", "OwnerPassword#2026")
        created = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@xorreset.test", "password": "AnalystOldPassword#2026!",
        })
        assert created.status_code == 201
        analyst_id = created.json()["id"]
        rejected = client.patch(f"/api/v1/organization/members/{analyst_id}", headers=owner_headers, json={
            "password": "AnalystNewPassword#2026@", "generate_temp": True,
        })
        assert rejected.status_code == 422
        assert rejected.json().get("temporary_password") is None
        assert client.post("/api/v1/auth/token", data={
            "username": "analyst@xorreset.test", "password": "AnalystOldPassword#2026!",
        }).status_code == 200
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_analyst_password_reset_accepts_active_only_change(monkeypatch):
    """PATCH exclusivo de active tiene éxito y no genera ninguna contraseña."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "ActiveOnlyOrg", "username": "owner@activeonly.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        }).status_code == 201
        owner_headers = _headers(client, "owner@activeonly.test", "OwnerPassword#2026")
        created = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@activeonly.test", "password": "AnalystBasePassword#2026!",
        })
        assert created.status_code == 201
        analyst_id = created.json()["id"]
        deactivated = client.patch(f"/api/v1/organization/members/{analyst_id}", headers=owner_headers, json={
            "active": False,
        })
        assert deactivated.status_code == 200
        assert deactivated.json()["active"] is False
        assert deactivated.json().get("temporary_password") is None
        assert client.post("/api/v1/auth/token", data={
            "username": "analyst@activeonly.test", "password": "AnalystBasePassword#2026!",
        }).status_code == 401
        reactivated = client.patch(f"/api/v1/organization/members/{analyst_id}", headers=owner_headers, json={
            "active": True,
        })
        assert reactivated.status_code == 200
        assert reactivated.json()["active"] is True
        assert reactivated.json().get("temporary_password") is None
        assert client.post("/api/v1/auth/token", data={
            "username": "analyst@activeonly.test", "password": "AnalystBasePassword#2026!",
        }).status_code == 200
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_analyst_password_reset_without_usable_alternative_is_rejected(monkeypatch):
    """Sin contraseña útil y sin generate_temp el PATCH se rechaza con 422."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        assert client.post("/api/v1/auth/register", json={
            "organization_name": "NoChangeOrg", "username": "owner@nochange.test",
            "password": "OwnerPassword#2026", "password_confirmation": "OwnerPassword#2026",
            "accepted_document_package_id": "SECURECODE-ONBOARDING", "accepted_document_package_version": "2026-11-20.1", "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b", "acceptance_confirmed": True,
        }).status_code == 201
        owner_headers = _headers(client, "owner@nochange.test", "OwnerPassword#2026")
        created = client.post("/api/v1/organization/members", headers=owner_headers, json={
            "username": "analyst@nochange.test", "password": "AnalystBasePassword#2026!",
        })
        assert created.status_code == 201
        analyst_id = created.json()["id"]
        assert client.patch(f"/api/v1/organization/members/{analyst_id}", headers=owner_headers, json={}).status_code == 422
        assert client.patch(f"/api/v1/organization/members/{analyst_id}", headers=owner_headers, json={
            "password": "",
        }).status_code == 422
        assert client.patch(f"/api/v1/organization/members/{analyst_id}", headers=owner_headers, json={
            "generate_temp": False,
        }).status_code == 422
        assert client.post("/api/v1/auth/token", data={
            "username": "analyst@nochange.test", "password": "AnalystBasePassword#2026!",
        }).status_code == 200
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()
