import json
import urllib.request
from urllib.error import HTTPError, URLError
from securecode.models.gh001 import GH001Evidence

def get_gh001_evidence(owner: str, repo: str, branch: str, token: str = None) -> GH001Evidence:
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
    url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}/protection"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
        
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
    except HTTPError as e:
        if e.code in (401, 403, 404):
            return GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
        raise RuntimeError(f"GitHub API returned unexpected HTTP status: {e.code}") from e
    except URLError as e:
        raise RuntimeError(f"Network error connecting to GitHub API: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise ValueError("Malformed JSON response from GitHub API") from e
        
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object from GitHub API")
        
    reviews = data.get("required_pull_request_reviews")
    if not reviews or not isinstance(reviews, dict):
        return GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
        
    return GH001Evidence(
        required_review_approvals=reviews.get("required_approving_review_count"),
        dismiss_stale_reviews=reviews.get("dismiss_stale_reviews")
    )
