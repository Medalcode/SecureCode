"""GH-002: verify GitHub evidence acquisition and rule evaluation together.

No network, PostgreSQL, secrets or running services are required.
The HTTP responses model an existing repository and branch followed by
three possible outcomes from the branch-protection endpoint.
"""
import json
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch

import pytest

from securecode.adapters.github import get_gh002_evidence
from securecode.engine.evaluator import evaluate_gh002


class MockHttpResponse:
    def __init__(self, payload):
        self.code = 200
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._data


@pytest.mark.parametrize(
    ("protection_http_status", "expected_protection", "expected_status"),
    [
        (200, True, "PASS"),
        (404, False, "FAIL"),
        (403, None, "UNKNOWN"),
    ],
    ids=["protected", "not-protected", "permission-denied"],
)
def test_gh002_acquisition_and_evaluation_matrix(
    protection_http_status, expected_protection, expected_status
):
    requested_urls = []

    def github_response(request):
        url = request.full_url
        requested_urls.append(url)
        if url == "https://api.github.com/repos/owner/repo":
            return MockHttpResponse({"default_branch": "main"})
        if url == "https://api.github.com/repos/owner/repo/branches/main":
            return MockHttpResponse({"name": "main"})
        if url == "https://api.github.com/repos/owner/repo/branches/main/protection":
            if protection_http_status != 200:
                raise HTTPError(url, protection_http_status, "Simulated GitHub status", {}, None)
            return MockHttpResponse({"required_pull_request_reviews": {}})
        raise AssertionError(f"Unexpected request to {url}")

    with patch("urllib.request.urlopen", side_effect=github_response):
        evidence = get_gh002_evidence("owner", "repo")

    assert evidence.default_branch == "main"
    assert evidence.protection_enabled is expected_protection
    assert evaluate_gh002(evidence).name == expected_status
    assert requested_urls == [
        "https://api.github.com/repos/owner/repo",
        "https://api.github.com/repos/owner/repo/branches/main",
        "https://api.github.com/repos/owner/repo/branches/main/protection",
    ]
