import pytest
from pydantic import ValidationError

from securecode.api.schemas import (
    GH001EvaluationRequest,
    GH002EvaluationRequest,
    GH003EvaluationRequest,
)


def test_evaluation_requests_normalize_safe_github_identifiers():
    request = GH001EvaluationRequest(
        owner=" Medalcode ", repository=" securecode-ground-truth ", branch=" main "
    )

    assert request.owner == "Medalcode"
    assert request.repository == "securecode-ground-truth"
    assert request.branch == "main"


@pytest.mark.parametrize("owner, repository", [
    ("Medal code", "repo"),
    ("Medalcode", "repo/path"),
    ("../../etc", "repo"),
])
def test_evaluation_requests_reject_unsafe_repository_identifiers(owner, repository):
    with pytest.raises(ValidationError):
        GH002EvaluationRequest(owner=owner, repository=repository)


@pytest.mark.parametrize("branch", ["feature//unsafe", "../main", "main.lock", "release candidate"])
def test_branch_controls_reject_invalid_github_references(branch):
    with pytest.raises(ValidationError):
        GH003EvaluationRequest(owner="Medalcode", repository="securecode-ground-truth", branch=branch)
