"""GH-001 evidence model for branch protection evaluation."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GH001Evidence:
    """GH-001 evidence: branch protection settings.
    
    Fields:
        required_review_approvals: Minimum number of required reviews (None if unavailable)
        dismiss_stale_reviews: Whether stale reviews are automatically dismissed (None if unavailable)
    """
    required_review_approvals: Optional[int] = None
    dismiss_stale_reviews: Optional[bool] = None
