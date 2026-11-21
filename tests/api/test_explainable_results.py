from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from securecode.api.app import app
from securecode.api.dependencies import get_current_user, get_db_session
from securecode.engine.types import EvaluationStatus
from securecode.models.gh001 import GH001Evidence
from securecode.ports.evaluation_repository import PersistedEvaluation

client = TestClient(app)
user_id = uuid4()


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _persisted(evidence: GH001Evidence, status: EvaluationStatus) -> PersistedEvaluation:
    return PersistedEvaluation(
        id=uuid4(),
        control_id="GH-001",
        rule_id="GH-001-RULE",
        rule_version=1,
        status=status,
        collected_at=datetime.now(UTC),
        evaluated_at=datetime.now(UTC),
        evidence_id=uuid4(),
        source_type="GitHub",
        source_repository="owner/repo",
        source_branch="main",
        reconstructed_evidence=evidence,
        requested_by_user_id=user_id,
    )


def _install_dependencies(persisted: PersistedEvaluation, *, current_user_id=user_id, role="analyst"):
    stored_record = MagicMock(
        requested_by_user_id=user_id,
        evidence=MagicMock(evidence_hash=persisted.reconstructed_evidence.canonical_hash()),
    )
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = stored_record
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: MagicMock(id=current_user_id, role=role)
    return stored_record


@patch("securecode.api.app.PostgresEvaluationRepository_Dependency_Wrapper")
def test_evaluation_detail_includes_explanation(mock_repository_factory):
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    persisted = _persisted(evidence, EvaluationStatus.PASS)
    _install_dependencies(persisted)
    mock_repository_factory.return_value.get_evaluation.return_value = persisted

    response = client.get(f"/api/v1/evaluations/{persisted.id}")

    assert response.status_code == 200
    explanation = response.json()["explanation"]
    assert explanation["summary"]["status"] == "PASS"
    assert [condition["status"] for condition in explanation["conditions"]] == ["PASS", "PASS"]
    assert explanation["evidence"]["integrity_valid"] is True
    assert explanation["normative_traceability"]["controls"][0]["id"] == "CM-3"


@patch("securecode.api.app.PostgresEvaluationRepository_Dependency_Wrapper")
def test_evaluation_pdf_is_protected_and_no_store(mock_repository_factory):
    evidence = GH001Evidence(required_review_approvals=1, dismiss_stale_reviews=False)
    persisted = _persisted(evidence, EvaluationStatus.FAIL)
    _install_dependencies(persisted)
    mock_repository_factory.return_value.get_evaluation.return_value = persisted

    response = client.get(f"/api/v1/evaluations/{persisted.id}/report.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"] == f'attachment; filename="securecode-gh-001-{persisted.id}.pdf"'
    assert response.content.startswith(b"%PDF-1.4")
    assert b"%%EOF" in response.content


@patch("securecode.api.app.PostgresEvaluationRepository_Dependency_Wrapper")
def test_evaluation_pdf_does_not_expose_other_tenant_records(mock_repository_factory):
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    persisted = _persisted(evidence, EvaluationStatus.PASS)
    _install_dependencies(persisted, current_user_id=uuid4())
    mock_repository_factory.return_value.get_evaluation.return_value = persisted

    response = client.get(f"/api/v1/evaluations/{persisted.id}/report.pdf")

    assert response.status_code == 404
    assert response.json()["detail"] == "Evaluation not found"
