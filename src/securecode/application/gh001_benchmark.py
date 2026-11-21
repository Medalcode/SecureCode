import hashlib
import json
from collections import Counter
from typing import Any

from securecode.engine.evaluator import evaluate_gh001
from securecode.models.gh001 import GH001Evidence

STATUSES = ("PASS", "FAIL", "UNKNOWN")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def evidence_from_case(case: dict[str, Any]) -> GH001Evidence | None:
    evidence = case.get("evidence")
    if isinstance(evidence, dict):
        return GH001Evidence(
            required_review_approvals=evidence.get("required_review_approvals"),
            dismiss_stale_reviews=evidence.get("dismiss_stale_reviews"),
        )
    if "expected_approvals" in case or "expected_dismiss_stale" in case:
        return GH001Evidence(
            required_review_approvals=case.get("expected_approvals"),
            dismiss_stale_reviews=case.get("expected_dismiss_stale"),
        )
    return None


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    evidence = evidence_from_case(case)
    actual = evaluate_gh001(evidence).name
    expected = str(case["expected_status"]).upper()
    return {
        "case_id": case["case_id"],
        "evidence": case.get("evidence"),
        "expected_status": expected,
        "actual_status": actual,
        "match": actual == expected,
    }


def build_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    results = [evaluate_case(case) for case in cases]
    confusion_matrix = {
        expected: {actual: 0 for actual in STATUSES}
        for expected in STATUSES
    }
    for result in results:
        confusion_matrix[result["expected_status"]][result["actual_status"]] += 1

    matched = sum(1 for result in results if result["match"])
    total = len(results)
    expected_distribution = Counter(result["expected_status"] for result in results)
    actual_distribution = Counter(result["actual_status"] for result in results)

    per_class = {}
    for status in STATUSES:
        support = sum(confusion_matrix[status].values())
        correct = confusion_matrix[status][status]
        predicted = sum(confusion_matrix[other][status] for other in STATUSES)
        precision = correct / predicted if predicted else None
        recall = correct / support if support else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else None
        )
        per_class[status] = {
            "support": support,
            "correct": correct,
            "incorrect": support - correct,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    return {
        "total_cases": total,
        "matched": matched,
        "mismatched": total - matched,
        "overall_accuracy": matched / total if total else None,
        "expected_distribution": {status: expected_distribution.get(status, 0) for status in STATUSES},
        "actual_distribution": {status: actual_distribution.get(status, 0) for status in STATUSES},
        "confusion_matrix": confusion_matrix,
        "per_class_metrics": per_class,
        "mismatches": [result for result in results if not result["match"]],
        "cases": results,
    }
