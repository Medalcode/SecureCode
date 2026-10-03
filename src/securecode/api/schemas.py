from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class GH001EvaluationRequest(BaseModel):
    owner: str = Field(..., min_length=1, description="GitHub repository owner")
    repository: str = Field(..., min_length=1, description="GitHub repository name")
    branch: str = Field(..., min_length=1, description="Branch to evaluate")

class SourceResponse(BaseModel):
    type: str
    repository: str
    branch: str

class RuleResponse(BaseModel):
    id: str
    version: int

class EvidenceResponse(BaseModel):
    required_review_approvals: Optional[int]
    dismiss_stale_reviews: Optional[bool]
    hash: str

class EvaluationResponse(BaseModel):
    evaluation_id: str
    control_id: str
    rule: Optional[RuleResponse]
    status: str
    source: SourceResponse
    evidence: EvidenceResponse
    collected_at: str
    evaluated_at: str

class GH002EvaluationRequest(BaseModel):
    owner: str = Field(..., min_length=1, description="GitHub repository owner")
    repository: str = Field(..., min_length=1, description="GitHub repository name")

class GH002EvidenceResponse(BaseModel):
    default_branch: str
    protection_enabled: Optional[bool]
    hash: str

class GH002EvaluationResponse(BaseModel):
    evaluation_id: str
    control_id: str
    rule: Optional[RuleResponse]
    status: str
    source: SourceResponse
    evidence: GH002EvidenceResponse
    collected_at: str
    evaluated_at: str
