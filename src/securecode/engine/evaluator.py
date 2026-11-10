"""Deterministic rule evaluator facade."""
import json
from pathlib import Path
from enum import Enum
from typing import Optional
from functools import lru_cache

from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence
from securecode.models.rules import RuleDefinition
from securecode.engine.types import EvaluationStatus
from securecode.engine.executor import evaluate_rule

_RULES_DIR = Path(__file__).parent.parent.parent.parent / "rules"

@lru_cache(maxsize=16)
def get_rule_definition(rule_file: str) -> RuleDefinition:
    """Load each canonical rule once per process, not once per request."""
    with open(_RULES_DIR / rule_file, "r") as f:
        return RuleDefinition(**json.load(f))

def evaluate_gh001(evidence: Optional[GH001Evidence], rule_definition: RuleDefinition | None = None) -> EvaluationStatus:
    """Evaluate GH-001 using canonical rule configuration."""
    rule_def = rule_definition or get_rule_definition("GH-001.json")
    return evaluate_rule(rule_def, evidence)

def evaluate_gh002(evidence: Optional[GH002Evidence], rule_definition: RuleDefinition | None = None) -> EvaluationStatus:
    """Evaluate GH-002 using canonical rule configuration."""
    rule_def = rule_definition or get_rule_definition("GH-002.json")
    return evaluate_rule(rule_def, evidence)


def evaluate_gh003(evidence: Optional[GH003Evidence], rule_definition: RuleDefinition | None = None) -> EvaluationStatus:
    """Evaluate whether GitHub enforces signed commits on the chosen branch."""
    rule_def = rule_definition or get_rule_definition("GH-003.json")
    return evaluate_rule(rule_def, evidence)
