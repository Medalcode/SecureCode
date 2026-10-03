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

from securecode.models.gh002 import GH002Evidence

def get_gh002_evidence(owner: str, repo: str, token: str = None) -> GH002Evidence:
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
            with urllib.request.urlopen(req) as response:
                return response.code, json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            return e.code, None
        except URLError as e:
            raise RuntimeError(f"Network error: {e.reason}") from e
            
    # Step 1: Get repository to find default_branch
    repo_url = f"https://api.github.com/repos/{owner}/{repo}"
    repo_status, repo_data = fetch_json(repo_url)
    if repo_status != 200 or not repo_data:
        # 404, 401, 403 -> UNKNOWN
        return GH002Evidence(default_branch="", protection_enabled=None)
        
    default_branch = repo_data.get("default_branch")
    if not default_branch:
        return GH002Evidence(default_branch="", protection_enabled=None)
        
    # Step 2: Verify branch exists
    branch_url = f"https://api.github.com/repos/{owner}/{repo}/branches/{default_branch}"
    branch_status, branch_data = fetch_json(branch_url)
    if branch_status != 200:
        return GH002Evidence(default_branch=default_branch, protection_enabled=None)
        
    # Step 3: Check branch protection
    protection_url = f"https://api.github.com/repos/{owner}/{repo}/branches/{default_branch}/protection"
    prot_status, prot_data = fetch_json(protection_url)
    
    if prot_status == 200:
        return GH002Evidence(default_branch=default_branch, protection_enabled=True)
    elif prot_status == 404:
        # We know repo & branch exist, so 404 precisely means NOT configured
        return GH002Evidence(default_branch=default_branch, protection_enabled=False)
    else:
        # 401, 403 -> UNKNOWN
        return GH002Evidence(default_branch=default_branch, protection_enabled=None)
