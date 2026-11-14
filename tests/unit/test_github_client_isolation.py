"""Network-isolation tests for the GitHub evidence adapter."""

from collections import deque

import pytest

from securecode.adapters.github import (
    LOCAL_TEST_GITHUB_API_BASE_URL,
    PRODUCTION_GITHUB_API_BASE_URL,
    TEST_BASE_URL_ENV,
    TEST_MODE_ENV,
    UrllibGitHubHttpClient,
    get_gh001_evidence,
    get_gh002_evidence,
    get_gh003_evidence,
    github_http_client_from_environment,
)


class LocalGitHubSimulator:
    """In-memory test transport: no socket or DNS access is possible."""

    def __init__(self, responses: list[tuple[int, dict | None]]) -> None:
        self.responses = deque(responses)
        self.requests: list[tuple[str, dict[str, str]]] = []

    def get_json(self, path: str, headers: dict[str, str]) -> tuple[int, dict | None]:
        self.requests.append((path, headers))
        return self.responses.popleft()


def test_injected_simulator_evaluates_all_controls_without_urlopen(monkeypatch):
    def fail_if_network_is_used(*args, **kwargs):
        raise AssertionError("The injected simulator must prevent network egress")

    monkeypatch.setattr("securecode.adapters.github.urllib.request.urlopen", fail_if_network_is_used)

    gh001 = LocalGitHubSimulator(
        [
            (200, {"default_branch": "main"}),
            (200, {"name": "main"}),
            (200, {"required_pull_request_reviews": {"required_approving_review_count": 2, "dismiss_stale_reviews": True}}),
        ]
    )
    gh002 = LocalGitHubSimulator(
        [(200, {"default_branch": "main"}), (200, {"name": "main"}), (200, {})]
    )
    gh003 = LocalGitHubSimulator([(200, {"name": "main"}), (200, {})])

    assert get_gh001_evidence("owner", "repo", "main", client=gh001).dismiss_stale_reviews is True
    assert get_gh002_evidence("owner", "repo", client=gh002).protection_enabled is True
    assert get_gh003_evidence("owner", "repo", "main", client=gh003).required_signatures_enabled is True
    assert gh001.requests[2][0].endswith("/protection")
    assert gh003.requests[1][0].endswith("/protection/required_signatures")


def test_runtime_client_ignores_legacy_arbitrary_base_url(monkeypatch):
    monkeypatch.delenv(TEST_MODE_ENV, raising=False)
    monkeypatch.setenv("GITHUB_API_BASE_URL", "https://example.invalid")

    client = github_http_client_from_environment()

    assert isinstance(client, UrllibGitHubHttpClient)
    assert client.base_url == PRODUCTION_GITHUB_API_BASE_URL


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.github.com",
        "http://localhost:8001",
        "http://127.0.0.1:9000",
        "https://example.invalid",
        "http://127.0.0.1:8001/proxy",
    ],
)
def test_test_mode_rejects_every_unapproved_destination(monkeypatch, base_url):
    monkeypatch.setenv(TEST_MODE_ENV, "1")
    monkeypatch.setenv(TEST_BASE_URL_ENV, base_url)

    with pytest.raises(ValueError, match="GitHub API base URL|approved local simulator"):
        github_http_client_from_environment()


def test_test_mode_accepts_only_the_fixed_loopback_simulator(monkeypatch):
    monkeypatch.setenv(TEST_MODE_ENV, "1")
    monkeypatch.setenv(TEST_BASE_URL_ENV, LOCAL_TEST_GITHUB_API_BASE_URL)

    client = github_http_client_from_environment()

    assert isinstance(client, UrllibGitHubHttpClient)
    assert client.base_url == LOCAL_TEST_GITHUB_API_BASE_URL


def test_fixed_loopback_client_bypasses_host_proxy_configuration(monkeypatch):
    class Response:
        status = 200

        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class DirectOpener:
        def __init__(self):
            self.request = None

        def open(self, request, timeout):
            self.request = request
            return Response()

    opener = DirectOpener()
    monkeypatch.setattr(
        "securecode.adapters.github.urllib.request.build_opener",
        lambda *handlers: opener,
    )

    status, payload = UrllibGitHubHttpClient(LOCAL_TEST_GITHUB_API_BASE_URL).get_json(
        "/repos/owner/repo", {}
    )

    assert (status, payload) == (200, {})
    assert opener.request.full_url.startswith(LOCAL_TEST_GITHUB_API_BASE_URL)


@pytest.mark.parametrize("path", ["https://api.github.com/repos/a/b", "//evil.invalid/path", "relative"])
def test_client_rejects_url_like_paths_before_any_network_request(path):
    client = UrllibGitHubHttpClient(PRODUCTION_GITHUB_API_BASE_URL)

    with pytest.raises(ValueError, match="path"):
        client.get_json(path, {})
