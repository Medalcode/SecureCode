import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timezone

from securecode.api.app import app
from securecode.engine.evaluator import EvaluationStatus
from securecode.ports.evaluation_repository import PersistedEvaluation
from securecode.models.gh002 import GH002Evidence
from securecode.api.dependencies import get_db_session

app.dependency_overrides[get_db_session] = lambda: None

client = TestClient(app)

def mock_persisted_gh002(status: EvaluationStatus, evidence: GH002Evidence):
    return PersistedEvaluation(
        id=uuid4(),
        control_id="GH-002",
        rule_id="GH-002-RULE",
        rule_version=1,
        status=status,
        collected_at=datetime.now(timezone.utc),
        evaluated_at=datetime.now(timezone.utc),
        evidence_id=uuid4(),
        source_type="GitHub",
        source_repository="owner/repo",
        source_branch=evidence.default_branch,
        reconstructed_evidence=evidence
    )

@patch("securecode.api.app.evaluate_and_store_gh002")
def test_gh002_pass(mock_eval):
    evidence = GH002Evidence(default_branch="main", protection_enabled=True)
    mock_eval.return_value = mock_persisted_gh002(EvaluationStatus.PASS, evidence)
    
    response = client.post("/api/v1/evaluations/gh-002", json={
        "owner": "owner",
        "repository": "repo"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PASS"
    assert data["evidence"]["protection_enabled"] is True

@patch("securecode.api.app.evaluate_and_store_gh002")
def test_gh002_unknown(mock_eval):
    evidence = GH002Evidence(default_branch="main", protection_enabled=None)
    mock_eval.return_value = mock_persisted_gh002(EvaluationStatus.UNKNOWN, evidence)
    
    response = client.post("/api/v1/evaluations/gh-002", json={
        "owner": "owner",
        "repository": "repo"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UNKNOWN"

@patch("securecode.api.app.evaluate_and_store_gh002")
def test_gh002_infrastructure_failure(mock_eval):
    mock_eval.side_effect = RuntimeError("Database connection failed")
    
    response = client.post("/api/v1/evaluations/gh-002", json={
        "owner": "owner",
        "repository": "repo"
    })
    
    assert response.status_code == 502

def test_gh002_invalid_input():
    response = client.post("/api/v1/evaluations/gh-002", json={
        "owner": "owner"
    })
    assert response.status_code == 422
