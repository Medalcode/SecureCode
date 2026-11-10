import pytest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from securecode.adapters.github import get_gh003_evidence
from securecode.engine.evaluator import EvaluationStatus, evaluate_gh003
from securecode.models.gh003 import GH003Evidence


def _response(status=200):
    response = MagicMock()
    response.status = status
    response.__enter__.return_value = response
    return response


def test_gh003_rule_pass_fail_and_unknown_are_deterministic():
    assert evaluate_gh003(GH003Evidence("main", True)) is EvaluationStatus.PASS
    assert evaluate_gh003(GH003Evidence("main", False)) is EvaluationStatus.FAIL
    assert evaluate_gh003(GH003Evidence("main", None)) is EvaluationStatus.UNKNOWN
    assert GH003Evidence("main", True).canonical_hash() == GH003Evidence("main", True).canonical_hash()


@patch("securecode.adapters.github.urllib.request.urlopen")
def test_gh003_adapter_detects_signed_commit_requirement(mock_urlopen):
    mock_urlopen.side_effect = [_response(), _response()]

    evidence = get_gh003_evidence("owner", "repo", "main", "token")

    assert evidence.branch == "main"
    assert evidence.required_signatures_enabled is True
    assert "/protection/required_signatures" in mock_urlopen.call_args_list[1].args[0].full_url


@patch("securecode.adapters.github.urllib.request.urlopen")
def test_gh003_adapter_distinguishes_disabled_from_unobservable(mock_urlopen):
    mock_urlopen.side_effect = [_response(), HTTPError("url", 404, "Not Found", {}, None)]
    assert get_gh003_evidence("owner", "repo", "main").required_signatures_enabled is False

    mock_urlopen.side_effect = [HTTPError("url", 403, "Forbidden", {}, None)]
    assert get_gh003_evidence("owner", "repo", "main").required_signatures_enabled is None
