import json
import re
from pathlib import Path

import pytest

from securecode.engine.evaluator import get_rules_directory
from securecode.models.rules import AndCondition, RuleDefinition

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLIANCE_DIR = REPO_ROOT / "docs" / "compliance"
TRACEABILITY = COMPLIANCE_DIR / "NIST-800-53-TRACEABILITY.md"
FICHES = COMPLIANCE_DIR / "CONTROL-FICHES.md"
SCOPE = COMPLIANCE_DIR / "SCOPE-AND-EXCLUSIONS.md"

EXPECTED_EVALUATORS = {
    "GH-001": "evaluate_gh001",
    "GH-002": "evaluate_gh002",
    "GH-003": "evaluate_gh003",
}

EXPECTED_MODELS = {
    "GH-001": "GH001Evidence",
    "GH-002": "GH002Evidence",
    "GH-003": "GH003Evidence",
}

EXPECTED_NIST = {
    "GH-001": ["CM-3", "CM-3(1)", "CM-5(4)"],
    "GH-002": ["CM-5", "CM-5(1)"],
    "GH-003": ["CM-14", "SI-7", "SI-7(1)", "SI-7(6)"],
}


def _canonical_rules(monkeypatch):
    monkeypatch.delenv("SECURECODE_RULES_DIR", raising=False)
    rules = {}
    for path in sorted(get_rules_directory().glob("GH-*.json")):
        definition = RuleDefinition(**json.loads(path.read_text(encoding="utf-8")))
        rules[definition.control_id] = (definition, path)
    return rules


def _render_condition(condition):
    if isinstance(condition, AndCondition):
        return " AND ".join(_render_condition(child) for child in condition.conditions)
    return f"{condition.field} {condition.operator} {json.dumps(condition.value)}"


def _section(text, heading):
    pattern = rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.MULTILINE)
    assert match, f"Missing section ## {heading}"
    return match.group(1)


def test_canonical_rules_are_documented(monkeypatch):
    rules = _canonical_rules(monkeypatch)
    assert set(rules) == set(EXPECTED_EVALUATORS)
    traceability = TRACEABILITY.read_text(encoding="utf-8")

    for control_id, (definition, path) in rules.items():
        section = _section(traceability, control_id)
        assert f"**Rule ID:** `{definition.rule_id}`" in section
        assert f"**Versión de regla:** `{definition.version}`" in section
        assert f"**Estado de regla:** `active={str(definition.active).lower()}`" in section
        assert f"**Archivo canónico:** `src/securecode/rules/{path.name}`" in section
        assert f"**Evaluador:** `{EXPECTED_EVALUATORS[control_id]}`" in section
        assert f"**Modelo de evidencia:** `{EXPECTED_MODELS[control_id]}`" in section
        assert f"**Condición canónica:** `{_render_condition(definition.condition)}`" in section
        for field in definition.allowlisted_fields:
            assert f"`{field}`" in section
        for nist_control in EXPECTED_NIST[control_id]:
            assert nist_control in section
        assert "parcial" in section.lower()
        assert "no implica certificación" in section.lower()


@pytest.mark.parametrize("control_id", sorted(EXPECTED_EVALUATORS))
def test_control_fiche_matches_canonical_rule(monkeypatch, control_id):
    definition, _ = _canonical_rules(monkeypatch)[control_id]
    section = _section(FICHES.read_text(encoding="utf-8"), f"Ficha {control_id}")

    assert f"| Rule ID | `{definition.rule_id}` |" in section
    assert f"| Versión de regla | `{definition.version}` |" in section
    assert f"| Activa | `{str(definition.active).lower()}` |" in section
    assert f"| Condición canónica | `{_render_condition(definition.condition)}` |" in section
    assert f"`{EXPECTED_EVALUATORS[control_id]}`" in section
    assert f"`{EXPECTED_MODELS[control_id]}`" in section
    for field in definition.allowlisted_fields:
        assert f"`{field}`" in section
    for state in ("PASS", "FAIL", "UNKNOWN"):
        assert f"`{state}`" in section
    for nist_control in EXPECTED_NIST[control_id]:
        assert nist_control in section
    assert "parcial" in section.lower()


def test_scope_and_exclusions_are_documented():
    scope = SCOPE.read_text(encoding="utf-8")
    assert "Cambios en el motor" in scope
    assert "Migraciones de base de datos" in scope
    assert "portada pública" in scope
    assert "no realiza entrevistas" in scope
    assert "correspondencias parciales" in scope.lower()
    assert "no implica certificación" in scope.lower()
