import json
import os
import urllib.request
from urllib.error import HTTPError, URLError
from urllib.parse import quote

from securecode.models.gh001 import GH001Evidence


def _github_timeout_seconds() -> float:
    """Bound outbound GitHub calls so a degraded upstream cannot pin a worker."""
    try:
        value = float(os.environ.get("GITHUB_API_TIMEOUT_SECONDS", "10"))
    except ValueError:
        return 10.0
    return min(max(value, 1.0), 60.0)


def _repository_api_url(owner: str, repo: str) -> str:
    """Build a GitHub API path without allowing path-segment injection."""
    return f"https://api.github.com/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"


def _branch_api_url(owner: str, repo: str, branch: str) -> str:
    return f"{_repository_api_url(owner, repo)}/branches/{quote(branch, safe='')}"

def get_gh001_evidence(owner: str, repo: str, branch: str, token: str | None = None) -> GH001Evidence:
    """
    Fetch branch protection evidence for GH-001 from GitHub API.
    
    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        branch: Branch name to check.
        token: Optional GitHub personal access token.
        
    Returns:
        GH001Evidence model. Missing protection or permissions will yield 
        None values, leading to an UNKNOWN evaluation.
        
    Raises:
        RuntimeError: For network errors or unexpected HTTP statuses (5xx).
        ValueError: For malformed JSON or unexpected top-level type.
    """
    headers = {"Accept": "application/vnd.github.v3+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def fetch_json(url: str) -> tuple[int, dict | None]:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=_github_timeout_seconds()) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("Expected JSON object from GitHub API")
                return response.status, payload
        except HTTPError as error:
            if error.code >= 500:
                raise RuntimeError(f"GitHub API returned unexpected HTTP status: {error.code}") from error
            return error.code, None
        except URLError as error:
            raise RuntimeError(f"Network error connecting to GitHub API: {error.reason}") from error
        except json.JSONDecodeError as error:
            raise ValueError("Malformed JSON response from GitHub API") from error

    # A protection endpoint 404 is only a reliable failure after confirming
    # that the repository and branch are both observable.
    repository_status, _ = fetch_json(_repository_api_url(owner, repo))
    if repository_status != 200:
        return GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
    branch_status, _ = fetch_json(_branch_api_url(owner, repo, branch))
    if branch_status != 200:
        return GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
    protection_status, data = fetch_json(f"{_branch_api_url(owner, repo, branch)}/protection")
    if protection_status == 404:
        return GH001Evidence(required_review_approvals=0, dismiss_stale_reviews=False)
    if protection_status != 200 or data is None:
        return GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)

    reviews = data.get("required_pull_request_reviews")
    if not reviews or not isinstance(reviews, dict):
        return GH001Evidence(required_review_approvals=0, dismiss_stale_reviews=False)
        
    return GH001Evidence(
        required_review_approvals=reviews.get("required_approving_review_count"),
        dismiss_stale_reviews=reviews.get("dismiss_stale_reviews")
    )

from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence


def get_gh002_evidence(owner: str, repo: str, token: str | None = None) -> GH002Evidence:
    """
    Fetch default branch protection evidence for GH-002 from GitHub API.
    
    This function handles the ambiguous 404 by sequentially checking:
    1. Repository exists (and gets default branch).
    2. Branch exists.
    3. Branch protection status.
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    def fetch_json(url):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=_github_timeout_seconds()) as response:
                return response.code, json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            if e.code >= 500:
                raise RuntimeError(f"GitHub API returned unexpected HTTP status: {e.code}") from e
            return e.code, None
        except URLError as e:
            raise RuntimeError(f"Network error: {e.reason}") from e
            
    # Step 1: Get repository to find default_branch
    repo_url = _repository_api_url(owner, repo)
    repo_status, repo_data = fetch_json(repo_url)
    if repo_status != 200 or not repo_data:
        # 404, 401, 403 -> UNKNOWN
        return GH002Evidence(default_branch="", protection_enabled=None)
        
    default_branch = repo_data.get("default_branch")
    if not default_branch:
        return GH002Evidence(default_branch="", protection_enabled=None)
        
    # Step 2: Verify branch exists
    branch_url = _branch_api_url(owner, repo, default_branch)
    branch_status, branch_data = fetch_json(branch_url)
    if branch_status != 200:
        return GH002Evidence(default_branch=default_branch, protection_enabled=None)

    # Step 3: Check branch protection
    protection_url = f"{_branch_api_url(owner, repo, default_branch)}/protection"
    prot_status, prot_data = fetch_json(protection_url)

    if prot_status == 200:
        return GH002Evidence(default_branch=default_branch, protection_enabled=True)
    elif prot_status == 404:
        # We know repo & branch exist, so 404 precisely means NOT configured
        return GH002Evidence(default_branch=default_branch, protection_enabled=False)
    else:
        # 401, 403 -> UNKNOWN
        return GH002Evidence(default_branch=default_branch, protection_enabled=None)


def get_gh003_evidence(owner: str, repo: str, branch: str, token: str | None = None) -> GH003Evidence:
    """Fetch the GitHub branch setting that requires signed commits.

    A 404 is a reliable non-conformance only after GitHub confirms that the
    branch exists. Access failures stay UNKNOWN to avoid treating missing
    evidence as a failed control.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def fetch_status(url: str) -> int:
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=_github_timeout_seconds()) as response:
                return response.status
        except HTTPError as error:
            if error.code >= 500:
                raise RuntimeError(f"GitHub API returned unexpected HTTP status: {error.code}") from error
            return error.code
        except URLError as error:
            raise RuntimeError(f"Network error: {error.reason}") from error

    branch_url = _branch_api_url(owner, repo, branch)
    if fetch_status(branch_url) != 200:
        return GH003Evidence(branch=branch, required_signatures_enabled=None)

    signatures_url = (
        _branch_api_url(owner, repo, branch)
        + "/protection/required_signatures"
    )
    signatures_status = fetch_status(signatures_url)
    if signatures_status == 200:
        return GH003Evidence(branch=branch, required_signatures_enabled=True)
    if signatures_status == 404:
        return GH003Evidence(branch=branch, required_signatures_enabled=False)
    return GH003Evidence(branch=branch, required_signatures_enabled=None)
