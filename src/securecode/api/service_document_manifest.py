import hashlib
import json
from pathlib import Path
from typing import Any

MANIFEST_PATH = Path(__file__).resolve().parents[3] / "docs" / "compliance" / "service_documents.manifest.json"
EXPECTED_MANIFEST_SHA256 = "163bab7d53ec3efa7d6ad5f8838621d49e14f2499c7691e07b79c766288d67fc"


def manifest_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_document_manifest() -> dict[str, Any]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if payload.get("manifest_version") != "1.0":
        raise RuntimeError("Unsupported service document manifest version")
    actual = manifest_sha256(payload)
    if actual != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("Service document manifest hash does not match the trusted reference")
    return payload
