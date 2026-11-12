"""GitHub evidence adapter with a constrained local-test seam."""

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit

from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence

PRODUCTION_GITHUB_API_BASE_URL = "https://api.github.com"
LOCAL_TEST_GITHUB_API_BASE_URL = "http://127.0.0.1:8001"
TEST_MODE_ENV = "SECURECODE_GITHUB_TEST_MODE"
TEST_BASE_URL_ENV = "SECURECODE_GITHUB_TEST_BASE_URL"


class GitHubHttpClient(Protocol):
    """Minimal outbound port used by evidence acquisition functions."""

    def get_json(self, path: str, headers: dict[str, str]) -> tuple[int, dict | None]:
        """Return a status and JSON object, or raise a transport error."""


def _github_timeout_seconds() -> float:
    try:
        value = float(os.environ.get("GITHUB_API_TIMEOUT_SECONDS", "10"))
    except ValueError:
        return 10.0
    return min(max(value, 1.0), 60.0)


def _validate_api_base_url(base_url: str, *, allow_local_test_endpoint: bool) -> str:
    """Permit only the public GitHub API or the fixed local test simulator."""
    parsed = urlsplit(base_url)
    normalized = base_url.rstrip("/")
    if normalized == PRODUCTION_GITHUB_API_BASE_URL:
        return normalized
    if (
        allow_local_test_endpoint
        and normalized == LOCAL_TEST_GITHUB_API_BASE_URL
        and parsed.scheme == "http"
        and parsed.hostname == "127.0.0.1"
        and parsed.port == 8001
        and not parsed.path
        and not parsed.query
        and not parsed.fragment
    ):
        return normalized
    raise ValueError(
        "GitHub API base URL is not permitted. Production uses api.github.com; "
        "test mode only permits http://127.0.0.1:8001."
    )


@dataclass(frozen=True)
class UrllibGitHubHttpClient:
    """HTTP client with a fixed, validated origin."""

    base_url: str = PRODUCTION_GITHUB_API_BASE_URL

    def __post_init__(self) -> None:
        _validate_api_base_url(
            self.base_url,
            allow_local_test_endpoint=self.base_url.rstrip("/")
            == LOCAL_TEST_GITHUB_API_BASE_URL,
        )

    def get_json(self, path: str, headers: dict[str, str]) -> tuple[int, dict | None]:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("GitHub API path must be an absolute path, not a URL.")
        request = urllib.request.Request(f"{self.base_url.rstrip('/')}{path}", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=_github_timeout_seconds()) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise TypeError("Expected JSON object from GitHub API")
                status = getattr(response, "status", None)
                if not isinstance(status, int):
                    status = getattr(response, "code", None)
                if not isinstance(status, int):
                    raise TypeError("GitHub API response did not include an HTTP status.")
                return status, payload
        except HTTPError as error:
            if error.code >= 500:
                raise RuntimeError(
                    f"GitHub API returned unexpected HTTP status: {error.code}"
                ) from error
            return error.code, None
        except URLError as error:
            raise RuntimeError(f"Network error connecting to GitHub API: {error.reason}") from error
        except json.JSONDecodeError as error:
            raise ValueError("Malformed JSON response from GitHub API") from error


def github_http_client_from_environment() -> GitHubHttpClient:
    """Build a runtime client without accepting arbitrary network destinations."""
    if os.environ.get(TEST_MODE_ENV) != "1":
        return UrllibGitHubHttpClient(PRODUCTION_GITHUB_API_BASE_URL)
    base_url = _validate_api_base_url(
        os.environ.get(TEST_BASE_URL_ENV, ""), allow_local_test_endpoint=True
    )
    if base_url != LOCAL_TEST_GITHUB_API_BASE_URL:
        raise ValueError("GitHub test mode requires the approved local simulator endpoint.")
    return UrllibGitHubHttpClient(base_url)


def _repository_api_path(owner: str, repo: str) -> str:
    return f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"


def _branch_api_path(owner: str, repo: str, branch: str) -> str:
    return f"{_repository_api_path(owner, repo)}/branches/{quote(branch, safe='')}"


def _headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_gh001_evidence(
    owner: str,
    repo: str,
    branch: str,
    token: str | None = None,
    *,
    client: GitHubHttpClient | None = None,
) -> GH001Evidence:
    """Fetch branch-review evidence for GH-001."""
    http_client = client or github_http_client_from_environment()
    headers = _headers(token)
    repository_status, _ = http_client.get_json(_repository_api_path(owner, repo), headers)
    if repository_status != 200:
        return GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
    branch_path = _branch_api_path(owner, repo, branch)
    branch_status, _ = http_client.get_json(branch_path, headers)
    if branch_status != 200:
        return GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
    protection_status, data = http_client.get_json(f"{branch_path}/protection", headers)
    if protection_status == 404:
        return GH001Evidence(required_review_approvals=0, dismiss_stale_reviews=False)
    if protection_status != 200 or data is None:
        return GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
    reviews = data.get("required_pull_request_reviews")
    if not isinstance(reviews, dict):
        return GH001Evidence(required_review_approvals=0, dismiss_stale_reviews=False)
    return GH001Evidence(
        required_review_approvals=reviews.get("required_approving_review_count"),
        dismiss_stale_reviews=reviews.get("dismiss_stale_reviews"),
    )


def get_gh002_evidence(
    owner: str,
    repo: str,
    token: str | None = None,
    *,
    client: GitHubHttpClient | None = None,
) -> GH002Evidence:
    """Fetch default-branch protection evidence for GH-002."""
    http_client = client or github_http_client_from_environment()
    headers = _headers(token)
    repository_status, repository_data = http_client.get_json(
        _repository_api_path(owner, repo), headers
    )
    if repository_status != 200 or repository_data is None:
        return GH002Evidence(default_branch="", protection_enabled=None)
    default_branch = repository_data.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        return GH002Evidence(default_branch="", protection_enabled=None)
    branch_path = _branch_api_path(owner, repo, default_branch)
    branch_status, _ = http_client.get_json(branch_path, headers)
    if branch_status != 200:
        return GH002Evidence(default_branch=default_branch, protection_enabled=None)
    protection_status, _ = http_client.get_json(f"{branch_path}/protection", headers)
    if protection_status == 200:
        return GH002Evidence(default_branch=default_branch, protection_enabled=True)
    if protection_status == 404:
        return GH002Evidence(default_branch=default_branch, protection_enabled=False)
    return GH002Evidence(default_branch=default_branch, protection_enabled=None)


def get_gh003_evidence(
    owner: str,
    repo: str,
    branch: str,
    token: str | None = None,
    *,
    client: GitHubHttpClient | None = None,
) -> GH003Evidence:
    """Fetch the GitHub branch setting that requires signed commits."""
    http_client = client or github_http_client_from_environment()
    headers = _headers(token)
    branch_path = _branch_api_path(owner, repo, branch)
    branch_status, _ = http_client.get_json(branch_path, headers)
    if branch_status != 200:
        return GH003Evidence(branch=branch, required_signatures_enabled=None)
    signatures_status, _ = http_client.get_json(
        f"{branch_path}/protection/required_signatures", headers
    )
    if signatures_status == 200:
        return GH003Evidence(branch=branch, required_signatures_enabled=True)
    if signatures_status == 404:
        return GH003Evidence(branch=branch, required_signatures_enabled=False)
    return GH003Evidence(branch=branch, required_signatures_enabled=None)
