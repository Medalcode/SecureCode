import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import UniqueConstraint, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from securecode.adapters.postgres.models import (
    Base,
    Organization,
    OrganizationMembership,
    User,
)
from securecode.api.app import _stored_evidence_hash, app
from securecode.api.dependencies import get_db_session
from securecode.models.gh001 import GH001Evidence


def _headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _register(client: TestClient, organization: str, username: str) -> None:
    response = client.post("/api/v1/auth/register", json={
        "organization_name": organization,
        "username": username,
        "password": "OwnerPassword#2026",
        "password_confirmation": "OwnerPassword#2026",
        "accepted_document_package_id": "SECURECODE-ONBOARDING",
        "accepted_document_package_version": "2026-11-20.1",
        "accepted_document_package_sha256": "0e5b8853f82fbe9109c516b945f16c63942f85686ebfcb01f9a6986e5d36bc7b",
        "acceptance_confirmed": True,
    })
    assert response.status_code == 201


def test_phase5_full_two_organization_flow(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    monkeypatch.setattr(
        "securecode.application.evaluate_and_store.get_gh001_evidence",
        lambda *args, **kwargs: GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True),
    )
    monkeypatch.setattr(
        "securecode.application.evaluate_and_store.get_gh002_evidence",
        lambda *args, **kwargs: SimpleNamespace(
            default_branch="main", protection_enabled=True, canonical_hash=lambda: "d" * 64
        ),
    )
    monkeypatch.setattr(
        "securecode.application.evaluate_and_store.get_gh003_evidence",
        lambda *args, **kwargs: SimpleNamespace(
            branch="main", required_signatures_enabled=False, canonical_hash=lambda: "e" * 64
        ),
    )

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        _register(client, "Audit Alpha", "owner@alpha.test")
        _register(client, "Audit Beta", "owner@beta.test")
        owner_a = _headers(client, "owner@alpha.test", "OwnerPassword#2026")
        owner_b = _headers(client, "owner@beta.test", "OwnerPassword#2026")

        analyst_a = client.post("/api/v1/organization/members", headers=owner_a, json={
            "username": "analyst@alpha.test", "password": "AnalystPassword#2026",
        })
        analyst_b = client.post("/api/v1/organization/members", headers=owner_b, json={
            "username": "analyst@beta.test", "password": "AnalystPassword#2026",
        })
        assert analyst_a.status_code == analyst_b.status_code == 201
        analyst_a_headers = _headers(client, "analyst@alpha.test", "AnalystPassword#2026")
        analyst_b_headers = _headers(client, "analyst@beta.test", "AnalystPassword#2026")

        for owner_headers, analyst_id, repository in (
            (owner_a, analyst_a.json()["id"], "alpha/app"),
            (owner_b, analyst_b.json()["id"], "beta/app"),
        ):
            authorization = client.post("/api/v1/organization/repository-authorizations", headers=owner_headers, json={
                "user_id": analyst_id, "repository": repository,
            })
            assert authorization.status_code == 201

        assert client.post("/api/v1/organization/repository-authorizations", headers=owner_a, json={
            "user_id": analyst_b.json()["id"], "repository": "alpha/app",
        }).status_code == 404

        ids: dict[str, str] = {}
        for headers, owner, repository in (
            (analyst_a_headers, "alpha", "alpha/app"),
            (analyst_b_headers, "beta", "beta/app"),
        ):
            gh001 = client.post("/api/v1/evaluations/gh-001", headers=headers, json={
                "owner": owner, "repository": "app", "branch": "main",
            })
            gh002 = client.post("/api/v1/evaluations/gh-002", headers=headers, json={
                "owner": owner, "repository": "app",
            })
            gh003 = client.post("/api/v1/evaluations/gh-003", headers=headers, json={
                "owner": owner, "repository": "app", "branch": "main",
            })
            assert gh001.status_code == gh002.status_code == gh003.status_code == 200
            assert [item.json()["status"] for item in (gh001, gh002, gh003)] == ["PASS", "PASS", "FAIL"]
            for item in (gh001, gh002, gh003):
                payload = item.json()
                assert payload["explanation"]["summary"]["status"] == payload["status"]
                assert payload["explanation"]["normative_traceability"]["correspondence"] == "parcial"
                assert payload["source"]["repository"] == repository
                ids[f"{owner}-{payload['control_id']}"] = payload["evaluation_id"]

        history_a = client.get("/api/v1/evaluations/history", headers=owner_a).json()["evaluations"]
        history_b = client.get("/api/v1/evaluations/history", headers=owner_b).json()["evaluations"]
        assert {item["repository"] for item in history_a} == {"alpha/app"}
        assert {item["repository"] for item in history_b} == {"beta/app"}
        assert len(history_a) == len(history_b) == 3

        evaluation_id = ids["alpha-GH-001"]
        detail = client.get(f"/api/v1/evaluations/{evaluation_id}", headers=owner_a)
        assert detail.status_code == 200
        assert detail.json()["explanation"]["evidence"]["integrity_valid"] is True
        assert client.get(f"/api/v1/evaluations/{evaluation_id}", headers=owner_b).status_code in (403, 404)

        pdf = client.get(f"/api/v1/evaluations/{evaluation_id}/report.pdf", headers=owner_a)
        assert pdf.status_code == 200
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF")
        assert "no-store" in pdf.headers["cache-control"]
        assert client.get(f"/api/v1/evaluations/{evaluation_id}/report.pdf", headers=owner_b).status_code in (403, 404)

        acceptances_a = client.get("/api/v1/organization/service-acceptances", headers=owner_a)
        acceptances_b = client.get("/api/v1/organization/service-acceptances", headers=owner_b)
        assert acceptances_a.status_code == acceptances_b.status_code == 200
        assert acceptances_a.json()
        assert acceptances_b.json()
        assert {item["document_id"] for item in acceptances_a.json()} == {
            item["document_id"] for item in acceptances_b.json()
        }
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_ambiguous_organization_membership_fails_closed(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    membership_table = OrganizationMembership.__table__
    single_membership_constraints = [
        constraint
        for constraint in list(membership_table.constraints)
        if isinstance(constraint, UniqueConstraint)
        and tuple(column.name for column in constraint.columns) == ("user_id",)
    ]
    for constraint in single_membership_constraints:
        membership_table.constraints.remove(constraint)
    try:
        Base.metadata.create_all(engine)
    finally:
        for constraint in single_membership_constraints:
            membership_table.constraints.add(constraint)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        client = TestClient(app)
        _register(client, "Audit Alpha", "owner@alpha.test")
        _register(client, "Audit Beta", "owner@beta.test")
        owner_a = _headers(client, "owner@alpha.test", "OwnerPassword#2026")
        alpha = session.query(Organization).filter(Organization.name == "Audit Alpha").one()
        beta = session.query(Organization).filter(Organization.name == "Audit Beta").one()
        owner = session.query(User).filter(User.username == "owner@alpha.test").one()
        session.add(OrganizationMembership(
            id=uuid4(),
            organization_id=beta.id,
            user_id=owner.id,
            role="owner",
            created_at=datetime.now(UTC),
        ))
        session.commit()

        response = client.get("/api/v1/evaluations/history", headers=owner_a)
        assert response.status_code == 409
        assert "Multiple organization memberships" in response.json()["detail"]
        assert alpha.id != beta.id
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_missing_stored_hash_is_treated_as_integrity_failure():
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    record = SimpleNamespace(evidence=None)
    persisted = SimpleNamespace(reconstructed_evidence=evidence)

    assert _stored_evidence_hash(record, persisted) == ""
