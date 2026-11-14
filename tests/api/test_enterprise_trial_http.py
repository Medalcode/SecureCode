"""HTTP contract tests for the non-billable Enterprise Trial lifecycle."""

from datetime import UTC, datetime
from unittest.mock import patch
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
from securecode.engine.evaluator import EvaluationStatus
from securecode.models.gh001 import GH001Evidence
from securecode.ports.evaluation_repository import PersistedEvaluation


@pytest.fixture
def trial_client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    user = User(
        id=uuid4(), username="trial.owner@example.com", password_hash=hash_password("TrialPassword#2026"),
        active=True, role="auditor", created_at=datetime.now(UTC),
    )
    session.add(user)
    session.commit()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        yield TestClient(app), {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_trial_activation_requires_confirmation_and_is_one_time(trial_client):
    client, headers = trial_client
    assert client.get("/api/v1/enterprise-trial", headers=headers).json()["status"] == "not_started"

    rejected = client.post("/api/v1/enterprise-trial", headers=headers, json={
        "organization_name": "Example Security", "confirmation": False,
    })
    assert rejected.status_code == 422

    created = client.post("/api/v1/enterprise-trial", headers=headers, json={
        "organization_name": "Example Security", "confirmation": True,
    })
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "active"
    assert body["organization_name"] == "Example Security"
    assert body["repository_limit"] == 3
    assert body["evaluation_limit"] == 100
    assert body["billing_mode"] == "trial_non_billable"

    duplicate = client.post("/api/v1/enterprise-trial", headers=headers, json={
        "organization_name": "Another name", "confirmation": True,
    })
    assert duplicate.status_code == 409


def test_trial_repository_scope_is_limited_and_idempotent(trial_client):
    client, headers = trial_client
    client.post("/api/v1/enterprise-trial", headers=headers, json={
        "organization_name": "Scope Example", "confirmation": True,
    })

    first = client.post("/api/v1/enterprise-trial/repositories", headers=headers, json={
        "repository": "Acme/One",
    })
    assert first.status_code == 200
    assert first.json()["repositories"] == ["acme/one"]

    repeated = client.post("/api/v1/enterprise-trial/repositories", headers=headers, json={
        "repository": "acme/one",
    })
    assert repeated.status_code == 200
    assert repeated.json()["repositories_used"] == 1

    for repository in ("Acme/Two", "Acme/Three"):
        assert client.post("/api/v1/enterprise-trial/repositories", headers=headers, json={
            "repository": repository,
        }).status_code == 200
    limit = client.post("/api/v1/enterprise-trial/repositories", headers=headers, json={
        "repository": "Acme/Four",
    })
    assert limit.status_code == 409
    assert "quota" in limit.json()["detail"]


def test_trial_endpoints_require_authentication(trial_client):
    client, _ = trial_client
    assert client.get("/api/v1/enterprise-trial").status_code == 401
    assert client.post("/api/v1/enterprise-trial", json={
        "organization_name": "No session", "confirmation": True,
    }).status_code == 401


@patch("securecode.api.app.evaluate_and_store_gh001")
def test_active_trial_enforces_scope_and_idempotency_for_evaluations(mock_evaluate, trial_client):
    client, headers = trial_client
    client.post("/api/v1/enterprise-trial", headers=headers, json={
        "organization_name": "Evaluation scope", "confirmation": True,
    })
    client.post("/api/v1/enterprise-trial/repositories", headers=headers, json={
        "repository": "Acme/One",
    })
    persisted = PersistedEvaluation(
        id=uuid4(), control_id="GH-001", rule_id="GH-001-RULE", rule_version=1,
        status=EvaluationStatus.PASS, collected_at=datetime.now(UTC), evaluated_at=datetime.now(UTC),
        evidence_id=uuid4(), source_type="GitHub", source_repository="acme/one", source_branch="main",
        reconstructed_evidence=GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True),
    )
    mock_evaluate.return_value = persisted

    missing_key = client.post("/api/v1/evaluations/gh-001", headers=headers, json={
        "owner": "Acme", "repository": "One", "branch": "main",
    })
    assert missing_key.status_code == 400

    first = client.post("/api/v1/evaluations/gh-001", headers={**headers, "Idempotency-Key": "trial-evaluation-1"}, json={
        "owner": "Acme", "repository": "One", "branch": "main",
    })
    assert first.status_code == 200
    status = client.get("/api/v1/enterprise-trial", headers=headers).json()
    assert status["evaluations_used"] == 1
    assert status["evaluations_remaining"] == 99

    duplicate = client.post("/api/v1/evaluations/gh-001", headers={**headers, "Idempotency-Key": "trial-evaluation-1"}, json={
        "owner": "Acme", "repository": "One", "branch": "main",
    })
    assert duplicate.status_code == 409
