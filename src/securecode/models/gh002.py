import hashlib
import json
from typing import Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class GH002Evidence:
    default_branch: str
    protection_enabled: Optional[bool]
    
    def canonical_hash(self) -> str:
        """
        Produce a deterministic SHA-256 hash of the evidence.
        """
        payload = {
            "control": "GH-002",
            "default_branch": self.default_branch,
            "protection_enabled": self.protection_enabled
        }
        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
