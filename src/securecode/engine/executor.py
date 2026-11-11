from typing import Any

from securecode.engine.types import EvaluationStatus
from securecode.models.rules import AndCondition, Condition, RuleDefinition


def evaluate_condition(cond: Condition, evidence: Any) -> EvaluationStatus:
    # Safely extract field from evidence (Pydantic model)
    if not hasattr(evidence, cond.field):
        return EvaluationStatus.UNKNOWN
        
    actual_value = getattr(evidence, cond.field)
    
    if actual_value is None:
        return EvaluationStatus.UNKNOWN
        
    expected_value = cond.value
    
    # Python considers bool a subclass of int. It must never satisfy a numeric
    # rule (for example, True must not pass GTE 1 or EQ 1).
    actual_is_number = isinstance(actual_value, (int, float)) and not isinstance(actual_value, bool)
    expected_is_number = isinstance(expected_value, (int, float)) and not isinstance(expected_value, bool)
    if cond.operator == "GTE" and not (actual_is_number and expected_is_number):
        return EvaluationStatus.UNKNOWN
    if cond.operator == "EQ" and type(actual_value) is not type(expected_value):
        # Numeric equality permits only real numeric values, never booleans.
        if not (actual_is_number and expected_is_number):
            return EvaluationStatus.UNKNOWN
            
    if cond.operator == "EQ":
        if actual_value == expected_value:
            return EvaluationStatus.PASS
        return EvaluationStatus.FAIL
        
    if cond.operator == "GTE":
        if actual_value >= expected_value:
            return EvaluationStatus.PASS
        return EvaluationStatus.FAIL
        
    return EvaluationStatus.UNKNOWN

def evaluate_rule(rule_definition: RuleDefinition, evidence: Any) -> EvaluationStatus:
    """
    Evaluates a RuleDefinition against a given Evidence model.
    """
    if evidence is None:
        return EvaluationStatus.UNKNOWN
        
    cond = rule_definition.condition
    
    if isinstance(cond, Condition):
        return evaluate_condition(cond, evidence)
        
    elif isinstance(cond, AndCondition):
        results = [evaluate_condition(c, evidence) for c in cond.conditions]
        
        # Three-valued logic for AND. A known violation is conclusive even
        # when another field is unavailable. UNKNOWN is reserved for cases
        # where no condition has failed but the available evidence is not
        # enough to prove compliance.
        if EvaluationStatus.FAIL in results:
            return EvaluationStatus.FAIL

        if EvaluationStatus.UNKNOWN in results:
            return EvaluationStatus.UNKNOWN
            
        return EvaluationStatus.PASS
        
    return EvaluationStatus.UNKNOWN
