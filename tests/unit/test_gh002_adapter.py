import pytest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError
from io import BytesIO

from securecode.adapters.github import get_gh002_evidence

def create_mock_response(status_code, json_str):
    mock = MagicMock()
    mock.code = status_code
    mock.read.return_value = json_str.encode('utf-8')
    mock.__enter__.return_value = mock
    return mock

@patch("urllib.request.urlopen")
def test_gh002_pass(mock_urlopen):
    # Step 1: Repo info (returns default_branch)
    repo_resp = create_mock_response(200, '{"default_branch": "main"}')
    # Step 2: Branch info (returns 200)
    branch_resp = create_mock_response(200, '{}')
    # Step 3: Protection info (returns 200)
    prot_resp = create_mock_response(200, '{}')
    
    mock_urlopen.side_effect = [repo_resp, branch_resp, prot_resp]
    
    evidence = get_gh002_evidence("owner", "repo")
    assert evidence.default_branch == "main"
    assert evidence.protection_enabled is True

@patch("urllib.request.urlopen")
def test_gh002_fail_not_protected(mock_urlopen):
    repo_resp = create_mock_response(200, '{"default_branch": "main"}')
    branch_resp = create_mock_response(200, '{}')
    
    # Step 3 throws HTTPError 404
    err_mock = MagicMock()
    err_mock.code = 404
    mock_urlopen.side_effect = [repo_resp, branch_resp, HTTPError("url", 404, "Not Found", {}, None)]
    
    evidence = get_gh002_evidence("owner", "repo")
    assert evidence.default_branch == "main"
    assert evidence.protection_enabled is False

@patch("urllib.request.urlopen")
def test_gh002_unknown_no_repo(mock_urlopen):
    mock_urlopen.side_effect = HTTPError("url", 404, "Not Found", {}, None)
    
    evidence = get_gh002_evidence("owner", "repo")
    assert evidence.protection_enabled is None

@patch("urllib.request.urlopen")
def test_gh002_unknown_unauthorized(mock_urlopen):
    repo_resp = create_mock_response(200, '{"default_branch": "main"}')
    branch_resp = create_mock_response(200, '{}')
    mock_urlopen.side_effect = [repo_resp, branch_resp, HTTPError("url", 401, "Unauthorized", {}, None)]
    
    evidence = get_gh002_evidence("owner", "repo")
    assert evidence.default_branch == "main"
    assert evidence.protection_enabled is None
