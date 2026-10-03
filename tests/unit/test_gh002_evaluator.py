import pytest
from securecode.engine.evaluator import evaluate_gh002, EvaluationStatus
from securecode.models.gh002 import GH002Evidence

def test_gh002_pass():
    evidence = GH002Evidence(default_branch="main", protection_enabled=True)
    assert evaluate_gh002(evidence) == EvaluationStatus.PASS

def test_gh002_fail():
    evidence = GH002Evidence(default_branch="main", protection_enabled=False)
    assert evaluate_gh002(evidence) == EvaluationStatus.FAIL

def test_gh002_unknown_missing_evidence():
    assert evaluate_gh002(None) == EvaluationStatus.UNKNOWN

def test_gh002_unknown_no_protection_info():
    evidence = GH002Evidence(default_branch="main", protection_enabled=None)
    assert evaluate_gh002(evidence) == EvaluationStatus.UNKNOWN
