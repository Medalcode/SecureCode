"""GH-001 evidence model for branch protection evaluation."""

import json
import hashlib
from dataclasses import dataclass, asdict
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

    def canonical_hash(self) -> str:
        """Calculate a deterministic SHA-256 hash of the evidence."""
        payload = {
            "control": "GH-001",
            "dismiss_stale_reviews": self.dismiss_stale_reviews,
            "required_review_approvals": self.required_review_approvals,
        }
        # Serialize with sorted keys and no spaces to ensure determinism
        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
