import json
from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

class ControlDefinition(BaseModel):
    control_id: str
    name: str
    description: str
    source_type: str = "GitHub"
    active: bool = True

class Condition(BaseModel):
    field: str
    operator: Literal["EQ", "GTE"]
    value: Any

class AndCondition(BaseModel):
    operator: Literal["AND"]
    conditions: List[Condition]

    @field_validator("conditions")
    def validate_conditions_not_empty(cls, v):
        if not v:
            raise ValueError("AND operator requires at least one condition")
        return v

RuleConditionType = Union[Condition, AndCondition]

class RuleDefinition(BaseModel):
    rule_id: str
    control_id: str
    version: int
    active: bool = True
    condition: RuleConditionType
    allowlisted_fields: List[str]

    @model_validator(mode='after')
    def validate_fields_against_allowlist(self):
        def extract_fields(cond: RuleConditionType) -> List[str]:
            if isinstance(cond, AndCondition):
                fields = []
                for c in cond.conditions:
                    fields.append(c.field)
                return fields
            else:
                return [cond.field]
                
        fields = extract_fields(self.condition)
        for f in fields:
            if f not in self.allowlisted_fields:
                raise ValueError(f"Field '{f}' is not allowlisted for this rule. Allowed: {self.allowlisted_fields}")
        return self
