import pytest
from securecode.engine.executor import evaluate_rule
from securecode.models.rules import RuleDefinition, Condition, AndCondition
from securecode.engine.types import EvaluationStatus
from securecode.models.gh001 import GH001Evidence
from pydantic import ValidationError

def test_executor_pass():
    rule = RuleDefinition(
        rule_id="test",
        control_id="c1",
        version=1,
        allowlisted_fields=["required_review_approvals"],
        condition=Condition(field="required_review_approvals", operator="GTE", value=2)
    )
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    assert evaluate_rule(rule, evidence) == EvaluationStatus.PASS

def test_executor_fail():
    rule = RuleDefinition(
        rule_id="test",
        control_id="c1",
        version=1,
        allowlisted_fields=["required_review_approvals"],
        condition=Condition(field="required_review_approvals", operator="GTE", value=2)
    )
    evidence = GH001Evidence(required_review_approvals=1, dismiss_stale_reviews=True)
    assert evaluate_rule(rule, evidence) == EvaluationStatus.FAIL

def test_executor_unknown_due_to_none():
    rule = RuleDefinition(
        rule_id="test",
        control_id="c1",
        version=1,
        allowlisted_fields=["required_review_approvals"],
        condition=Condition(field="required_review_approvals", operator="GTE", value=2)
    )
    evidence = GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=True)
    assert evaluate_rule(rule, evidence) == EvaluationStatus.UNKNOWN

def test_executor_and_condition_with_one_unknown():
    rule = RuleDefinition(
        rule_id="test",
        control_id="c1",
        version=1,
        allowlisted_fields=["required_review_approvals", "dismiss_stale_reviews"],
        condition=AndCondition(
            operator="AND",
            conditions=[
                Condition(field="required_review_approvals", operator="GTE", value=2),
                Condition(field="dismiss_stale_reviews", operator="EQ", value=True)
            ]
        )
    )
    # One field is missing -> should resolve to UNKNOWN (not FAIL), preserving strict semantics
    evidence = GH001Evidence(required_review_approvals=0, dismiss_stale_reviews=None)
    assert evaluate_rule(rule, evidence) == EvaluationStatus.UNKNOWN

def test_rule_validation_rejects_unknown_operator():
    with pytest.raises(ValidationError):
        RuleDefinition(
            rule_id="test",
            control_id="c1",
            version=1,
            allowlisted_fields=["f1"],
            condition={"field": "f1", "operator": "INVALID", "value": 1}
        )

def test_rule_validation_rejects_unallowlisted_field():
    with pytest.raises(ValueError, match="is not allowlisted"):
        RuleDefinition(
            rule_id="test",
            control_id="c1",
            version=1,
            allowlisted_fields=["allowed_field"],
            condition=Condition(field="disallowed_field", operator="EQ", value=1)
        )

def test_mutation_test_changes_behavior():
    rule_v1 = RuleDefinition(
        rule_id="test",
        control_id="c1",
        version=1,
        allowlisted_fields=["required_review_approvals"],
        condition=Condition(field="required_review_approvals", operator="GTE", value=2)
    )
    
    rule_v2 = RuleDefinition(
        rule_id="test",
        control_id="c1",
        version=2,
        allowlisted_fields=["required_review_approvals"],
        condition=Condition(field="required_review_approvals", operator="GTE", value=3)
    )
    
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    
    assert evaluate_rule(rule_v1, evidence) == EvaluationStatus.PASS
    assert evaluate_rule(rule_v2, evidence) == EvaluationStatus.FAIL
