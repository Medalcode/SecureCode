"""GH-001 deterministic rule evaluator."""

from enum import Enum
from typing import Optional
from src.models.gh001 import GH001Evidence


class EvaluationStatus(Enum):
    """Status of a rule evaluation."""
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


def evaluate_gh001(evidence: Optional[GH001Evidence]) -> EvaluationStatus:
    """
    Evaluate GH-001: Branch Protection Required.
    
    Conditions:
    - required_review_approvals >= 2
    - dismiss_stale_reviews == True
    
    Returns:
        PASS: Both conditions satisfied
        FAIL: Evidence exists but conditions violated
        UNKNOWN: Evidence is None or required fields are unavailable
    
    Raises:
        ValueError: On malformed programming/data-contract errors
    """
    if evidence is None:
        return EvaluationStatus.UNKNOWN
    
    approvals = evidence.required_review_approvals
    dismiss = evidence.dismiss_stale_reviews
    
    if approvals is None or dismiss is None:
        return EvaluationStatus.UNKNOWN
    
    if approvals >= 2 and dismiss is True:
        return EvaluationStatus.PASS
    
    return EvaluationStatus.FAIL
