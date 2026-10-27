import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"
os.environ["JWT_ALGORITHM"] = "HS256"

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timezone

from securecode.api.app import app
from securecode.api.dependencies import get_current_user, get_db_session
from securecode.api.security import create_access_token, hash_password

class DummyUser:
    def __init__(self, id, username, password_hash, active):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.active = active

mock_user_id = uuid4()
mock_user = DummyUser(
    id=mock_user_id,
    username="auditor@empresa.com",
    password_hash=hash_password("Password123!"),
    active=True
)

class DummyRecord:
    def __init__(self, id, control_id, status, source_repository, source_branch, evaluated_at, evidence_hash):
        self.id = id
        self.control_id = control_id
        self.status = status
        self.source_repository = source_repository
        self.source_branch = source_branch
        self.evaluated_at = evaluated_at
        self.evidence = MagicMock()
        self.evidence.evidence_hash = evidence_hash

def test_list_evaluations_unauthorized():
    app.dependency_overrides.clear()
    client = TestClient(app)
    resp = client.get("/api/v1/evaluations")
    assert resp.status_code == 401

def test_list_evaluations_authorized_success():
    client = TestClient(app)
    token = create_access_token(str(mock_user_id))

    dummy_rec = DummyRecord(
        id=uuid4(),
        control_id="GH-001",
        status="PASS",
        source_repository="acme-corp/payment-gateway",
        source_branch="main",
        evaluated_at=datetime.now(timezone.utc),
        evidence_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )

    mock_session = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        with patch("securecode.api.app.PostgresEvaluationRepository_Dependency_Wrapper") as mock_repo_wrapper:
            mock_repo = MagicMock()
            mock_repo.list_evaluations.return_value = (1, [dummy_rec])
            mock_repo_wrapper.return_value = mock_repo

            resp = client.get(
                "/api/v1/evaluations?status=PASS&search=payment",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            item = data["items"][0]
            assert item["control"] == "GH-001"
            assert item["verdict"] == "PASS"
            assert item["repository_and_branch"] == "acme-corp/payment-gateway (main)"
            assert item["evaluation_id"].startswith("eval_")
            assert item["hash_sha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            assert "Mostrando 1 de 1 registros" in data["pagination_info"]
    finally:
        app.dependency_overrides.clear()
