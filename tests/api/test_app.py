import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timezone

from securecode.api.app import app
from securecode.engine.evaluator import EvaluationStatus
from securecode.ports.evaluation_repository import PersistedEvaluation
from securecode.models.gh001 import GH001Evidence
from securecode.api.dependencies import get_db_session
from securecode.adapters.postgres.models import User
from securecode.api.security import create_access_token

os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["JWT_ALGORITHM"] = "HS256"

from securecode.api.security import hash_password

class DummyUser:
    def __init__(self, id, username, password_hash, active):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.active = active

mock_user_id = uuid4()
mock_user = DummyUser(
    id=mock_user_id,
    username="testuser",
    password_hash=hash_password("correctpassword"),
    active=True
)

def mock_session():
    class MockQuery:
        def __init__(self, model):
            self.model = model
            self.filters = []
            
        def filter(self, *args):
            self.filters.extend(args)
            return self
            
        def first(self):
            if not self.filters:
                return None
            expr = self.filters[0]
            val = getattr(getattr(expr, "right", None), "value", None)
            if str(val) == "testuser":
                return mock_user
            if str(val) == str(mock_user_id):
                return mock_user
            return None

    class _MockSession:
        def query(self, model):
            return MockQuery(model)

    return _MockSession()

@pytest.fixture(autouse=True)
def setup_mock_session():
    app.dependency_overrides[get_db_session] = mock_session
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

valid_token = create_access_token(str(mock_user_id))
auth_headers = {"Authorization": f"Bearer {valid_token}"}

def mock_persisted_evaluation(status: EvaluationStatus, evidence: GH001Evidence):
    return PersistedEvaluation(
        id=uuid4(),
        control_id="GH-001",
        rule_id="GH-001-RULE",
        rule_version=1,
        status=status,
        collected_at=datetime.now(timezone.utc),
        evaluated_at=datetime.now(timezone.utc),
        evidence_id=uuid4(),
        source_type="GitHub",
        source_repository="owner/repo",
        source_branch="main",
        reconstructed_evidence=evidence
    )

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("securecode.api.app.evaluate_and_store_gh001")
def test_gh001_pass(mock_eval):
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    mock_eval.return_value = mock_persisted_evaluation(EvaluationStatus.PASS, evidence)
    
    response = client.post("/api/v1/evaluations/gh-001", headers=auth_headers, json={
        "owner": "Medalcode",
        "repository": "repo",
        "branch": "main"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PASS"
    assert data["evidence"]["required_review_approvals"] == 2

@patch("securecode.api.app.evaluate_and_store_gh001")
def test_gh001_unknown(mock_eval):
    evidence = GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
    mock_eval.return_value = mock_persisted_evaluation(EvaluationStatus.UNKNOWN, evidence)
    
    response = client.post("/api/v1/evaluations/gh-001", headers=auth_headers, json={
        "owner": "Medalcode",
        "repository": "repo",
        "branch": "main"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UNKNOWN"

@patch("securecode.api.app.evaluate_and_store_gh001")
def test_gh001_infrastructure_failure(mock_eval):
    mock_eval.side_effect = RuntimeError("Database connection failed")
    
    response = client.post("/api/v1/evaluations/gh-001", headers=auth_headers, json={
        "owner": "Medalcode",
        "repository": "repo",
        "branch": "main"
    })
    
    assert response.status_code == 502
    assert response.json()["detail"] == "Infrastructure or upstream communication failure"

def test_gh001_invalid_input():
    # Missing branch
    response = client.post("/api/v1/evaluations/gh-001", headers=auth_headers, json={
        "owner": "Medalcode",
        "repository": "repo"
    })
    assert response.status_code == 422
