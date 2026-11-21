import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from securecode.api.app import app
from securecode.api.dependencies import (
    get_current_user,
    get_db_session,
    get_github_token,
    require_platform_admin,
)
from securecode.domain.roles import PLATFORM_ADMIN
from securecode.engine.evaluator import EvaluationStatus
from securecode.models.gh001 import GH001Evidence
from securecode.observability import (
    REQUEST_ID_HEADER,
    JsonFormatter,
    get_metrics_snapshot,
    get_request_id,
    log_event,
    request_id_context,
    reset_metrics,
)
from securecode.ports.evaluation_repository import PersistedEvaluation

client = TestClient(app)


class _Query:
    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return None


class _Session:
    def query(self, model):
        return _Query()

    def commit(self):
        return None

    def rollback(self):
        return None

    def add(self, item):
        return None


class _User:
    def __init__(self, user_id: UUID):
        self.id = user_id
        self.role = PLATFORM_ADMIN
        self.active = True
        self.username = "observability-admin"


@pytest.fixture
def evaluation_client():
    app.dependency_overrides[get_db_session] = lambda: _Session()
    app.dependency_overrides[get_current_user] = lambda: _User(uuid4())
    app.dependency_overrides[get_github_token] = lambda: "test-token"
    yield TestClient(app)
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_github_token, None)


def _persisted_evaluation(status: EvaluationStatus) -> PersistedEvaluation:
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
        reconstructed_evidence=GH001Evidence(
            required_review_approvals=2,
            dismiss_stale_reviews=True,
        ),
    )


def test_request_id_is_validated_and_returned():
    supplied = "client_correlation_123"
    response = client.get("/health", headers={REQUEST_ID_HEADER: supplied})
    assert response.headers[REQUEST_ID_HEADER] == supplied

    malicious = "../../etc/passwd"
    response = client.get("/health", headers={REQUEST_ID_HEADER: malicious})
    generated = response.headers[REQUEST_ID_HEADER]
    assert generated != malicious
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", generated)


def test_json_formatter_emits_allowlisted_fields_and_redacts_secrets(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    with request_id_context("formatter_request_1"):
        record = logging.LogRecord(
            "securecode.observability",
            logging.ERROR,
            __file__,
            1,
            "ignored %s",
            ("secret-value",),
            None,
        )
        record.event = "http.request.failed"
        record.method = "POST"
        record.route = "/api/v1/evaluations/gh-001"
        record.status_code = 500
        record.duration_ms = 12.3456
        record.authorization = "Bearer jwt-secret"
        record.password = "password-secret"
        payload = json.loads(JsonFormatter().format(record))

    assert payload["timestamp"].endswith("Z")
    assert payload["level"] == "ERROR"
    assert payload["event"] == "http.request.failed"
    assert payload["service"] == "securecode"
    assert payload["environment"] == "test"
    assert payload["request_id"] == "formatter_request_1"
    assert payload["route"] == "/api/v1/evaluations/gh-001"
    assert "authorization" not in payload
    assert "password" not in payload
    assert "secret" not in json.dumps(payload)


def test_request_id_context_is_isolated_across_concurrent_tasks():
    async def worker(value: str) -> str:
        with request_id_context(value):
            await asyncio.sleep(0.001)
            return get_request_id()

    values = [f"concurrent_{index}" for index in range(20)]

    async def run_workers() -> list[str]:
        return await asyncio.gather(*(worker(value) for value in values))

    results = asyncio.run(run_workers())
    assert results == values


def test_metrics_endpoint_is_protected_and_uses_low_cardinality_labels():
    reset_metrics()
    raw_identifier = uuid4().hex
    assert client.get(f"/api/v1/nonexistent/{raw_identifier}").status_code == 404

    unauthorized = client.get("/internal/observability/metrics")
    assert unauthorized.status_code in (401, 403)

    app.dependency_overrides[require_platform_admin] = lambda: SimpleNamespace(role=PLATFORM_ADMIN)
    try:
        response = client.get("/internal/observability/metrics")
    finally:
        app.dependency_overrides.pop(require_platform_admin, None)
    assert response.status_code == 200

    snapshot = response.json()
    rendered = json.dumps(snapshot)
    assert raw_identifier not in rendered
    http_counters = [
        counter for counter in snapshot["counters"] if counter["name"] == "http_requests_total"
    ]
    unmatched_counter = next(
        counter
        for counter in http_counters
        if counter["labels"]["route"] == "unmatched" and counter["labels"]["status_class"] == "4xx"
    )
    assert unmatched_counter["labels"]["method"] == "GET"
    assert all(raw_identifier not in json.dumps(counter) for counter in http_counters)
    assert "password" not in rendered
    assert "authorization" not in rendered


@patch("securecode.api.app.readiness_status", return_value=(True, "ok"))
def test_liveness_and_ready_health_endpoints(mock_readiness):
    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "alive", "service": "securecode"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "reason": "ok"}
    mock_readiness.assert_called_once()


@patch("securecode.api.app.readiness_status", return_value=(False, "database_unavailable"))
def test_readiness_returns_503_without_internal_details(mock_readiness):
    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "reason": "database_unavailable"}
    assert "DATABASE_URL" not in response.text
    mock_readiness.assert_called_once()


def test_failed_security_result_is_not_a_critical_error(evaluation_client, caplog):
    reset_metrics()
    with patch(
        "securecode.api.app.evaluate_and_store_gh001",
        return_value=_persisted_evaluation(EvaluationStatus.FAIL),
    ), caplog.at_level(logging.DEBUG, logger="securecode.observability"):
        response = evaluation_client.post(
            "/api/v1/evaluations/gh-001",
            json={"owner": "owner", "repository": "repo", "branch": "main"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "FAIL"
    assert not [record for record in caplog.records if record.levelno >= logging.ERROR]
    snapshot = get_metrics_snapshot()
    evaluation_counter = next(
        counter for counter in snapshot["counters"] if counter["name"] == "evaluations_total"
    )
    assert evaluation_counter["labels"] == {
        "control": "GH-001",
        "result": "FAIL",
        "outcome": "RESULT",
    }


def test_unknown_security_result_is_not_a_critical_error(evaluation_client, caplog):
    reset_metrics()
    with patch(
        "securecode.api.app.evaluate_and_store_gh001",
        return_value=_persisted_evaluation(EvaluationStatus.UNKNOWN),
    ), caplog.at_level(logging.DEBUG, logger="securecode.observability"):
        response = evaluation_client.post(
            "/api/v1/evaluations/gh-001",
            json={"owner": "owner", "repository": "repo", "branch": "main"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "UNKNOWN"
    assert not [record for record in caplog.records if record.levelno >= logging.ERROR]


def test_evaluation_technical_error_is_critical_and_metered(evaluation_client, caplog):
    reset_metrics()
    with patch(
        "securecode.api.app.evaluate_and_store_gh001",
        side_effect=RuntimeError("upstream failure with token hypersecret"),
    ), caplog.at_level(logging.DEBUG, logger="securecode.observability"):
        response = evaluation_client.post(
            "/api/v1/evaluations/gh-001",
            json={"owner": "owner", "repository": "repo", "branch": "main"},
        )

    assert response.status_code == 502
    critical = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "evaluation.technical_error"
    ]
    assert len(critical) == 1
    assert critical[0].levelno == logging.ERROR
    assert critical[0].error_type == "RuntimeError"
    assert "hypersecret" not in critical[0].getMessage()
    snapshot = get_metrics_snapshot()
    error_counter = next(
        counter
        for counter in snapshot["counters"]
        if counter["name"] == "evaluations_total" and counter["labels"]["outcome"] == "TECHNICAL_ERROR"
    )
    assert error_counter["labels"]["result"] == "NONE"


def test_structured_logs_do_not_include_security_cookies_or_tokens(caplog):
    with caplog.at_level(logging.DEBUG, logger="securecode.observability"):
        log_event(logging.INFO, "privacy.check", password="hunter2")
    rendered = "\n".join(JsonFormatter().format(record) for record in caplog.records)
    assert "hunter2" not in rendered
    assert "password" not in rendered
