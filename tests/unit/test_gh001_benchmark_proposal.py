import hashlib
import json
from pathlib import Path

import pytest

from securecode.application.gh001_benchmark import build_metrics, canonical_sha256
from securecode.engine.evaluator import evaluate_gh001
from securecode.models.gh001 import GH001Evidence

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_ROOT = REPO_ROOT / "docs" / "benchmark" / "gh001"
V1_SNAPSHOT = BENCH_ROOT / "v1" / "gh001_benchmark_105_v1.snapshot.json"
V2_DATASET = BENCH_ROOT / "v2" / "gh001_benchmark_105_v2.proposed.json"
V2_SHA256 = BENCH_ROOT / "v2" / "gh001_benchmark_105_v2.proposed.json.sha256"
V1_METRICS = BENCH_ROOT / "results" / "gh001_v1_metrics.json"
V2_METRICS = BENCH_ROOT / "results" / "gh001_v2_proposed_metrics.json"

DISCREPANCY_IDS = {
    "GT-GH001-BENCH-071",
    "GT-GH001-BENCH-072",
    "GT-GH001-BENCH-073",
    "GT-GH001-BENCH-074",
    "GT-GH001-BENCH-076",
    "GT-GH001-BENCH-079",
    "GT-GH001-BENCH-081",
    "GT-GH001-BENCH-083",
    "GT-GH001-BENCH-085",
    "GT-GH001-BENCH-086",
    "GT-GH001-BENCH-088",
    "GT-GH001-BENCH-091",
    "GT-GH001-BENCH-093",
    "GT-GH001-BENCH-095",
}


@pytest.mark.parametrize(
    ("approvals", "dismiss", "expected"),
    [
        (3, True, "PASS"),
        (2, True, "PASS"),
        (1, True, "FAIL"),
        (0, True, "FAIL"),
        (3, False, "FAIL"),
        (1, False, "FAIL"),
        (0, False, "FAIL"),
        (3, None, "UNKNOWN"),
        (1, None, "FAIL"),
        (0, None, "FAIL"),
        (None, True, "UNKNOWN"),
        (None, False, "FAIL"),
        (None, None, "UNKNOWN"),
    ],
)
def test_gh001_tristate_contract(approvals, dismiss, expected):
    evidence = GH001Evidence(required_review_approvals=approvals, dismiss_stale_reviews=dismiss)
    assert evaluate_gh001(evidence).name == expected


def test_v1_snapshot_keeps_historical_hash():
    actual = hashlib.sha256(V1_SNAPSHOT.read_bytes()).hexdigest()
    assert actual == "8319425d25a1b251f680282495e22a11043093397cf36afcd88a77a1529d7947"


def test_v2_proposal_preserves_identifiers_and_evidence():
    v1 = json.loads(V1_SNAPSHOT.read_text(encoding="utf-8"))
    v2 = json.loads(V2_DATASET.read_text(encoding="utf-8"))
    assert [case["case_id"] for case in v1["cases"]] == [case["case_id"] for case in v2["cases"]]
    assert [case["evidence"] for case in v1["cases"]] == [case["evidence"] for case in v2["cases"]]

    changed = {
        case["case_id"]
        for first, case in zip(v1["cases"], v2["cases"])
        if first["expected_status"] != case["expected_status"]
    }
    assert changed == DISCREPANCY_IDS
    assert all(case["expected_status"] == "FAIL" for case in v2["cases"] if case["case_id"] in DISCREPANCY_IDS)
    assert v2["status"] == "PROPOSED_NOT_ADOPTED"
    assert v2["cases_canonical_sha256"] == canonical_sha256(v2["cases"])


def test_v2_proposal_hash_sidecar_matches():
    actual = hashlib.sha256(V2_DATASET.read_bytes()).hexdigest()
    assert V2_SHA256.read_text(encoding="utf-8").strip() == actual


def test_benchmark_metrics_artifacts_are_reproducible():
    v1 = json.loads(V1_SNAPSHOT.read_text(encoding="utf-8"))
    v2 = json.loads(V2_DATASET.read_text(encoding="utf-8"))
    v1_metrics = json.loads(V1_METRICS.read_text(encoding="utf-8"))
    v2_metrics = json.loads(V2_METRICS.read_text(encoding="utf-8"))

    recomputed_v1 = build_metrics(v1["cases"])
    recomputed_v2 = build_metrics(v2["cases"])

    assert (v1_metrics["matched"], v1_metrics["mismatched"]) == (91, 14)
    assert (v2_metrics["matched"], v2_metrics["mismatched"]) == (105, 0)
    assert v1_metrics["confusion_matrix"] == recomputed_v1["confusion_matrix"]
    assert v2_metrics["confusion_matrix"] == recomputed_v2["confusion_matrix"]
    assert {item["case_id"] for item in v1_metrics["mismatches"]} == DISCREPANCY_IDS
