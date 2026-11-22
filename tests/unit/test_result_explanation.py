from securecode.api.normative_transparency import SCOPE_WARNING
from securecode.application.result_explanation import build_result_explanation
from securecode.engine.types import EvaluationStatus
from securecode.models.gh001 import GH001Evidence
from securecode.models.gh003 import GH003Evidence


def test_gh001_pass_explanation_is_exact_and_traceable():
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    explanation = build_result_explanation(
        control_id="GH-001",
        rule_id="GH-001-RULE",
        rule_version=1,
        status=EvaluationStatus.PASS,
        evidence=evidence,
        evidence_hash=evidence.canonical_hash(),
    )

    assert explanation["summary"]["status"] == "PASS"
    assert explanation["rule"]["expression"] == "required_review_approvals GTE 2 AND dismiss_stale_reviews EQ true"
    assert [condition["status"] for condition in explanation["conditions"]] == ["PASS", "PASS"]
    assert [control["id"] for control in explanation["normative_traceability"]["controls"]] == [
        "CM-3",
        "CM-3(1)",
        "CM-5(4)",
    ]
    assert explanation["normative_traceability"]["correspondence"] == "parcial"
    assert explanation["normative_traceability"]["disclaimer"] == SCOPE_WARNING
    assert explanation["evidence"]["integrity_valid"] is True
    assert explanation["reconstruction"]["consistent_with_stored_status"] is True


def test_gh001_fail_explains_each_violation_and_recommends_remediation():
    evidence = GH001Evidence(required_review_approvals=1, dismiss_stale_reviews=False)
    explanation = build_result_explanation(
        control_id="GH-001",
        rule_id="GH-001-RULE",
        rule_version=1,
        status=EvaluationStatus.FAIL,
        evidence=evidence,
        evidence_hash=evidence.canonical_hash(),
    )

    assert [condition["status"] for condition in explanation["conditions"]] == ["FAIL", "FAIL"]
    assert "aprobaciones" in explanation["summary"]["reason"].lower()
    recommendations = " ".join(explanation["recommendations"]).lower()
    assert "dos aprobaciones" in recommendations
    assert "descarte automático" in recommendations


def test_unknown_is_not_reported_as_fail():
    evidence = GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
    explanation = build_result_explanation(
        control_id="GH-001",
        rule_id="GH-001-RULE",
        rule_version=1,
        status=EvaluationStatus.UNKNOWN,
        evidence=evidence,
        evidence_hash=evidence.canonical_hash(),
    )

    assert explanation["summary"]["status"] == "UNKNOWN"
    assert "No equivale a FAIL" in explanation["summary"]["note"]
    assert [condition["status"] for condition in explanation["conditions"]] == ["UNKNOWN", "UNKNOWN"]
    assert any("permisos de lectura" in item for item in explanation["recommendations"])


def test_integrity_mismatch_warns_without_overriding_stored_status():
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    explanation = build_result_explanation(
        control_id="GH-001",
        rule_id="GH-001-RULE",
        rule_version=1,
        status=EvaluationStatus.PASS,
        evidence=evidence,
        evidence_hash="0" * 64,
    )

    assert explanation["summary"]["status"] == "PASS"
    assert explanation["evidence"]["integrity_valid"] is False
    assert any("huella reconstruida" in warning.lower() for warning in explanation["reconstruction"]["warnings"])


def test_status_conflict_is_explicit_without_overriding_stored_status():
    evidence = GH001Evidence(required_review_approvals=1, dismiss_stale_reviews=False)
    explanation = build_result_explanation(
        control_id="GH-001",
        rule_id="GH-001-RULE",
        rule_version=1,
        status=EvaluationStatus.PASS,
        evidence=evidence,
        evidence_hash=evidence.canonical_hash(),
    )

    assert explanation["summary"]["status"] == "PASS"
    assert "ADVERTENCIA" in explanation["summary"]["reason"]
    assert "produce FAIL" in explanation["summary"]["reason"]
    assert any("No modificar el dictamen histórico" in item for item in explanation["recommendations"])
    assert explanation["reconstruction"]["consistent_with_stored_status"] is False


def test_gh003_nist_mapping_avoids_withdrawn_cm_5_3():
    evidence = GH003Evidence(branch="main", required_signatures_enabled=True)
    explanation = build_result_explanation(
        control_id="GH-003",
        rule_id="GH-003-RULE",
        rule_version=1,
        status=EvaluationStatus.PASS,
        evidence=evidence,
        evidence_hash=evidence.canonical_hash(),
    )

    controls = [control["id"] for control in explanation["normative_traceability"]["controls"]]
    assert controls == ["CM-14", "SI-7", "SI-7(1)", "SI-7(6)"]
    assert "CM-5(3)" not in controls
