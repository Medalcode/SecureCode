import json
import pytest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

from securecode.adapters.github import get_gh001_evidence, get_gh002_evidence
from securecode.engine.evaluator import evaluate_gh001, EvaluationStatus

@pytest.fixture
def mock_urlopen():
    with patch("urllib.request.urlopen") as mock:
        yield mock

def _create_mock_response(data, status=200):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(data).encode("utf-8")
    # To support context manager `with urlopen(...) as response:`
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp


def _observable_branch_responses(protection_payload):
    return [
        _create_mock_response({"default_branch": "main"}),
        _create_mock_response({"name": "main"}),
        _create_mock_response(protection_payload),
    ]

def test_github_adapter_success_pass(mock_urlopen):
    """1, 2: Successful complete response resulting in PASS (approvals=2, dismiss=true)"""
    mock_urlopen.side_effect = _observable_branch_responses({
        "required_pull_request_reviews": {
            "required_approving_review_count": 2,
            "dismiss_stale_reviews": True
        }
    })
    
    evidence = get_gh001_evidence("owner", "repo", "main")
    assert evidence.required_review_approvals == 2
    assert evidence.dismiss_stale_reviews is True
    
    # Integration style assertion
    assert evaluate_gh001(evidence) == EvaluationStatus.PASS

def test_github_adapter_success_fail_low_approvals(mock_urlopen):
    """3: Approvals below required threshold"""
    mock_urlopen.side_effect = _observable_branch_responses({
        "required_pull_request_reviews": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True
        }
    })
    
    evidence = get_gh001_evidence("owner", "repo", "main")
    assert evidence.required_review_approvals == 1
    assert evaluate_gh001(evidence) == EvaluationStatus.FAIL

def test_github_adapter_success_fail_no_dismiss(mock_urlopen):
    """4: dismiss_stale = false"""
    mock_urlopen.side_effect = _observable_branch_responses({
        "required_pull_request_reviews": {
            "required_approving_review_count": 2,
            "dismiss_stale_reviews": False
        }
    })
    
    evidence = get_gh001_evidence("owner", "repo", "main")
    assert evidence.dismiss_stale_reviews is False
    assert evaluate_gh001(evidence) == EvaluationStatus.FAIL

def test_github_adapter_missing_protection_is_non_conformant(mock_urlopen):
    """A 404 after repository and branch checks proves protection is absent."""
    mock_urlopen.side_effect = [
        _create_mock_response({"default_branch": "main"}),
        _create_mock_response({"name": "main"}),
        HTTPError("url", 404, "Not Found", {}, None),
    ]
    
    evidence = get_gh001_evidence("owner", "repo", "main")
    assert evidence.required_review_approvals == 0
    assert evidence.dismiss_stale_reviews is False
    assert evaluate_gh001(evidence) == EvaluationStatus.FAIL

def test_github_adapter_no_review_requirement_is_non_conformant(mock_urlopen):
    """An observable protected branch without review settings is a FAIL."""
    mock_urlopen.side_effect = _observable_branch_responses({
        "required_status_checks": {}
    })
    
    evidence = get_gh001_evidence("owner", "repo", "main")
    assert evidence.required_review_approvals == 0
    assert evidence.dismiss_stale_reviews is False
    assert evaluate_gh001(evidence) == EvaluationStatus.FAIL

def test_github_adapter_permission_failure(mock_urlopen):
    """7: authentication/permission failure (403 or 401)"""
    mock_urlopen.side_effect = HTTPError("url", 403, "Forbidden", {}, None)
    
    evidence = get_gh001_evidence("owner", "repo", "main")
    assert evidence.required_review_approvals is None
    assert evaluate_gh001(evidence) == EvaluationStatus.UNKNOWN

def test_github_adapter_repo_not_found(mock_urlopen):
    """8: repository or branch not found (404)"""
    mock_urlopen.side_effect = HTTPError("url", 404, "Not Found", {}, None)
    
    evidence = get_gh001_evidence("owner", "repo", "main")
    assert evidence.required_review_approvals is None
    assert evaluate_gh001(evidence) == EvaluationStatus.UNKNOWN

def test_github_adapter_malformed_response(mock_urlopen):
    """9: malformed unexpected response (non-JSON or non-dict)"""
    # Non-JSON
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"Not JSON"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp
    
    with pytest.raises(ValueError, match="Malformed JSON"):
        get_gh001_evidence("owner", "repo", "main")
        
    # JSON array instead of object
    mock_urlopen.return_value = _create_mock_response([1, 2, 3])
    with pytest.raises(ValueError, match="Expected JSON object"):
        get_gh001_evidence("owner", "repo", "main")

def test_github_adapter_network_failure(mock_urlopen):
    """10: network/HTTP failure (e.g. 500 or URLError)"""
    # HTTP 500
    mock_urlopen.side_effect = HTTPError("url", 500, "Internal Server Error", {}, None)
    with pytest.raises(RuntimeError, match="unexpected HTTP status"):
        get_gh001_evidence("owner", "repo", "main")
        
    # URLError
    mock_urlopen.side_effect = URLError("Name or service not known")
    with pytest.raises(RuntimeError, match="Network error"):
        get_gh001_evidence("owner", "repo", "main")


def test_github_urls_encode_branch_path_segments(mock_urlopen):
    mock_urlopen.side_effect = _observable_branch_responses({
        "required_pull_request_reviews": {"required_approving_review_count": 2, "dismiss_stale_reviews": True}
    })

    get_gh001_evidence("owner", "repo", "release/2026")

    assert "/branches/release%2F2026" in mock_urlopen.call_args_list[1].args[0].full_url


def test_gh002_upstream_server_errors_are_not_misclassified_as_unknown(mock_urlopen):
    mock_urlopen.side_effect = HTTPError("url", 503, "Unavailable", {}, None)

    with pytest.raises(RuntimeError, match="unexpected HTTP status: 503"):
        get_gh002_evidence("owner", "repo")
