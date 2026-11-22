from datetime import UTC, datetime

from securecode.application.evaluation_report import build_evaluation_report_pdf
from securecode.application.result_explanation import build_result_explanation
from securecode.engine.types import EvaluationStatus
from securecode.models.gh001 import GH001Evidence


def _explanation(evidence: GH001Evidence, status: EvaluationStatus) -> dict:
    return build_result_explanation(
        control_id="GH-001",
        rule_id="GH-001-RULE",
        rule_version=1,
        status=status,
        evidence=evidence,
        evidence_hash=evidence.canonical_hash(),
    )


def test_evaluation_pdf_has_valid_structure_and_explainable_sections():
    evidence = GH001Evidence(required_review_approvals=1, dismiss_stale_reviews=False)
    generated_at = datetime(2026, 11, 21, 12, 30, tzinfo=UTC)
    pdf = build_evaluation_report_pdf(
        evaluation_id="11111111-1111-1111-1111-111111111111",
        control_id="GH-001",
        status="FAIL",
        source_repository="owner/repo",
        source_branch="main",
        collected_at="2026-11-21T12:00:00+00:00",
        evaluated_at="2026-11-21T12:00:01+00:00",
        explanation=_explanation(evidence, EvaluationStatus.FAIL),
        generated_at=generated_at,
    )

    assert pdf.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf
    assert b"startxref" in pdf
    assert b"/Type /Catalog" in pdf
    assert b"/Type /Pages" in pdf
    assert b"/F2 12 Tf" in pdf

    text = pdf.decode("cp1252", errors="replace")
    assert "11111111-1111-1111-1111-111111111111" in text
    assert "GH-001" in text
    assert "CM-3" in text
    assert "Condiciones contrastadas" in text
    assert "Recomendaciones" in text
    assert "no certifica" in text.lower()
