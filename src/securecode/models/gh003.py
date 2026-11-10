"""GH-003 evidence model for signed-commit enforcement."""

import hashlib
import json
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GH003Evidence:
    """Evidence that GitHub requires signed commits on the selected branch."""

    branch: str
    required_signatures_enabled: Optional[bool]

    def canonical_hash(self) -> str:
        payload = {
            "branch": self.branch,
            "control": "GH-003",
            "required_signatures_enabled": self.required_signatures_enabled,
        }
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
