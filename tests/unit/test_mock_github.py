"""Contract tests for the local-only GitHub simulator used by performance runs."""

import pytest
from fastapi.testclient import TestClient

from scripts.mock_github import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MOCK_GITHUB_LATENCY_SECONDS", "0")
    monkeypatch.setenv("MOCK_GITHUB_SCENARIO", "PASS")
    return TestClient(app)


def test_pass_contract_covers_all_three_controls(client):
    repository = client.get("/repos/owner/repo")
    branch = client.get("/repos/owner/repo/branches/main")
    protection = client.get("/repos/owner/repo/branches/main/protection")
    signatures = client.get("/repos/owner/repo/branches/main/protection/required_signatures")

    assert repository.status_code == 200
    assert repository.json()["default_branch"] == "main"
    assert branch.status_code == 200
    assert protection.json()["required_pull_request_reviews"]["required_approving_review_count"] == 2
    assert signatures.status_code == 200


@pytest.mark.parametrize(
    ("scenario", "expected_status"),
    [
        ("UNAUTHORIZED", 401),
        ("FORBIDDEN", 403),
        ("NOT_FOUND", 404),
        ("RATE_LIMITED", 429),
        ("SERVER_ERROR", 500),
    ],
)
def test_upstream_failure_contracts_are_reproducible(client, monkeypatch, scenario, expected_status):
    monkeypatch.setenv("MOCK_GITHUB_SCENARIO", scenario)

    response = client.get("/repos/owner/repo")

    assert response.status_code == expected_status


def test_nonconformance_contracts_keep_branch_observable(client, monkeypatch):
    monkeypatch.setenv("MOCK_GITHUB_SCENARIO", "UNPROTECTED")

    assert client.get("/repos/owner/repo/branches/main").status_code == 200
    assert client.get("/repos/owner/repo/branches/main/protection").status_code == 404
    assert client.get("/repos/owner/repo/branches/main/protection/required_signatures").status_code == 404
