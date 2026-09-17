"""Unit tests for GH-001 deterministic evaluator."""

import pytest
from securecode.engine.evaluator import evaluate_gh001, EvaluationStatus
from securecode.models.gh001 import GH001Evidence


class TestGH001Evaluator:
    """Tests for GH-001 deterministic evaluation."""

    def test_pass_valid_evidence(self):
        """PASS: evidence with approvals=2, dismiss_stale=True"""
        evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
        result = evaluate_gh001(evidence)
        assert result == EvaluationStatus.PASS

    def test_pass_approvals_above_minimum(self):
        """PASS: evidence with approvals=3 (above minimum)"""
        evidence = GH001Evidence(required_review_approvals=3, dismiss_stale_reviews=True)
        result = evaluate_gh001(evidence)
        assert result == EvaluationStatus.PASS

    def test_fail_approvals_below_2(self):
        """FAIL: evidence with approvals=1"""
        evidence = GH001Evidence(required_review_approvals=1, dismiss_stale_reviews=True)
        result = evaluate_gh001(evidence)
        assert result == EvaluationStatus.FAIL

    def test_fail_approvals_zero(self):
        """FAIL: evidence with approvals=0"""
        evidence = GH001Evidence(required_review_approvals=0, dismiss_stale_reviews=True)
        result = evaluate_gh001(evidence)
        assert result == EvaluationStatus.FAIL

    def test_fail_dismiss_stale_false(self):
        """FAIL: evidence with dismiss_stale=False"""
        evidence = GH001Evidence(required_review_approvals=3, dismiss_stale_reviews=False)
        result = evaluate_gh001(evidence)
        assert result == EvaluationStatus.FAIL

    def test_fail_both_conditions_violated(self):
        """FAIL: evidence with approvals=1, dismiss_stale=False"""
        evidence = GH001Evidence(required_review_approvals=1, dismiss_stale_reviews=False)
        result = evaluate_gh001(evidence)
        assert result == EvaluationStatus.FAIL

    def test_unknown_missing_approvals(self):
        """UNKNOWN: evidence with missing required_review_approvals"""
        evidence = GH001Evidence(dismiss_stale_reviews=True)
        result = evaluate_gh001(evidence)
        assert result == EvaluationStatus.UNKNOWN

    def test_unknown_missing_dismiss_stale(self):
        """UNKNOWN: evidence with missing dismiss_stale_reviews"""
        evidence = GH001Evidence(required_review_approvals=2)
        result = evaluate_gh001(evidence)
        assert result == EvaluationStatus.UNKNOWN

    def test_unknown_both_fields_missing(self):
        """UNKNOWN: evidence with both fields missing"""
        evidence = GH001Evidence()
        result = evaluate_gh001(evidence)
        assert result == EvaluationStatus.UNKNOWN

    def test_unknown_none_evidence(self):
        """UNKNOWN: evidence=None"""
        result = evaluate_gh001(None)
        assert result == EvaluationStatus.UNKNOWN

    def test_reproducibility_10x(self):
        """PASS: same evidence produces same result 10 times"""
        evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
        results = [evaluate_gh001(evidence) for _ in range(10)]
        assert all(r == EvaluationStatus.PASS for r in results)
        assert len(set(results)) == 1

    def test_determinism_100x(self):
        """PASS: same evidence produces same result 100 times"""
        evidence = GH001Evidence(required_review_approvals=3, dismiss_stale_reviews=True)
        results = [evaluate_gh001(evidence) for _ in range(100)]
        assert all(r == EvaluationStatus.PASS for r in results)
        assert len(set(results)) == 1
