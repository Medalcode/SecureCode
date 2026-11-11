from datetime import datetime, timezone
from uuid import UUID
from unittest.mock import patch

import pytest

from securecode.application.evaluate_and_store import (
    evaluate_and_store_gh001,
    evaluate_and_store_gh002,
    evaluate_and_store_gh003,
)
from securecode.engine.evaluator import EvaluationStatus
from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence
from securecode.ports.evaluation_repository import PersistedEvaluation


class RepositorySpy:
    """In-memory port implementation that checks the application orchestration."""

    def __init__(self, control_id: str, evidence):
        self.control_id = control_id
        self.evidence = evidence
        self.saved: dict | None = None
        self.return_none = False

    def _save(self, **kwargs) -> None:
        self.saved = kwargs

    save_gh001_evaluation = _save
    save_gh002_evaluation = _save
    save_gh003_evaluation = _save

    def get_evaluation(self, evaluation_id: UUID):
        if self.return_none:
            return None
        assert self.saved is not None
        return PersistedEvaluation(
            id=evaluation_id,
            control_id=self.control_id,
            rule_id=self.saved["rule_id"],
            rule_version=self.saved["rule_version"],
            status=self.saved["status"],
            collected_at=self.saved["collected_at"],
            evaluated_at=self.saved["evaluated_at"],
            evidence_id=self.saved["evidence_id"],
            source_type="GitHub",
            source_repository=self.saved["source_repository"],
            source_branch=self.saved["source_branch"],
            reconstructed_evidence=self.evidence,
        )


@pytest.mark.parametrize(
    ("control_id", "function", "patch_target", "evidence", "args", "expected_branch"),
    [
        (
            "GH-001",
            evaluate_and_store_gh001,
            "securecode.application.evaluate_and_store.get_gh001_evidence",
            GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True),
            ("owner", "repo", "main", "token"),
            "main",
        ),
        (
            "GH-002",
            evaluate_and_store_gh002,
            "securecode.application.evaluate_and_store.get_gh002_evidence",
            GH002Evidence(default_branch="trunk", protection_enabled=True),
            ("owner", "repo", "token"),
            "trunk",
        ),
        (
            "GH-003",
            evaluate_and_store_gh003,
            "securecode.application.evaluate_and_store.get_gh003_evidence",
            GH003Evidence(branch="release/2026", required_signatures_enabled=True),
            ("owner", "repo", "release/2026", "token"),
            "release/2026",
        ),
    ],
)
def test_orchestrators_acquire_evaluate_persist_and_retrieve(
    control_id, function, patch_target, evidence, args, expected_branch,
):
    repository = RepositorySpy(control_id, evidence)
    with patch(patch_target, return_value=evidence) as acquire:
        persisted = function(*args, repository=repository)

    acquire.assert_called_once()
    assert repository.saved is not None
    assert repository.saved["status"] is EvaluationStatus.PASS
    assert repository.saved["source_repository"] == "owner/repo"
    assert repository.saved["source_branch"] == expected_branch
    assert persisted.reconstructed_evidence == evidence
    assert persisted.rule_id == f"{control_id}-RULE"


@pytest.mark.parametrize(
    ("function", "patch_target", "evidence", "args"),
    [
        (
            evaluate_and_store_gh001,
            "securecode.application.evaluate_and_store.get_gh001_evidence",
            GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None),
            ("owner", "repo", "main", "token"),
        ),
        (
            evaluate_and_store_gh002,
            "securecode.application.evaluate_and_store.get_gh002_evidence",
            GH002Evidence(default_branch="", protection_enabled=None),
            ("owner", "repo", "token"),
        ),
        (
            evaluate_and_store_gh003,
            "securecode.application.evaluate_and_store.get_gh003_evidence",
            GH003Evidence(branch="main", required_signatures_enabled=None),
            ("owner", "repo", "main", "token"),
        ),
    ],
)
def test_orchestrators_reject_unreadable_persisted_result(function, patch_target, evidence, args):
    repository = RepositorySpy("GH-001", evidence)
    repository.return_none = True
    with patch(patch_target, return_value=evidence), pytest.raises(RuntimeError, match="could not be retrieved"):
        function(*args, repository=repository)
