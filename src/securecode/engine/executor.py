from typing import Any
from securecode.engine.types import EvaluationStatus
from securecode.models.rules import RuleDefinition, Condition, AndCondition

def evaluate_condition(cond: Condition, evidence: Any) -> EvaluationStatus:
    # Safely extract field from evidence (Pydantic model)
    if not hasattr(evidence, cond.field):
        return EvaluationStatus.UNKNOWN
        
    actual_value = getattr(evidence, cond.field)
    
    if actual_value is None:
        return EvaluationStatus.UNKNOWN
        
    expected_value = cond.value
    
    # Type checking if possible
    if type(actual_value) != type(expected_value):
        # We might have int vs float, but let's be strict for our use case (bool, int)
        if not (isinstance(actual_value, (int, float)) and isinstance(expected_value, (int, float))):
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
        
        # Three-valued logic for AND:
        # If any condition is UNKNOWN, the result is UNKNOWN (missing evidence propagates).
        # This matches the strictly defined semantics of GH-001 (returns UNKNOWN if any required field is None).
        if EvaluationStatus.UNKNOWN in results:
            return EvaluationStatus.UNKNOWN
            
        if EvaluationStatus.FAIL in results:
            return EvaluationStatus.FAIL
            
        return EvaluationStatus.PASS
        
    return EvaluationStatus.UNKNOWN
