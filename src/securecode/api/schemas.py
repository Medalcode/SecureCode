import re

from pydantic import BaseModel, Field, field_validator

_GITHUB_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
_INVALID_BRANCH_FRAGMENT = re.compile(r"[\s~^:?*\[\\\\]")


class GitHubRepositoryRequest(BaseModel):
    """Shared, deliberately strict input contract for GitHub evaluations."""

    owner: str = Field(..., min_length=1, max_length=100, description="GitHub repository owner")
    repository: str = Field(..., min_length=1, max_length=100, description="GitHub repository name")

    @field_validator("owner", "repository")
    @classmethod
    def validate_github_name(cls, value: str) -> str:
        normalized = value.strip()
        if not _GITHUB_NAME.fullmatch(normalized):
            raise ValueError("Debe ser un identificador de GitHub válido, sin espacios ni rutas.")
        return normalized


class GitHubBranchRequest(GitHubRepositoryRequest):
    branch: str = Field(..., min_length=1, max_length=255, description="Branch to evaluate")

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, value: str) -> str:
        normalized = value.strip()
        if (
            not normalized
            or normalized.startswith(("/", "."))
            or normalized.endswith(("/", ".", ".lock"))
            or ".." in normalized
            or "//" in normalized
            or _INVALID_BRANCH_FRAGMENT.search(normalized)
        ):
            raise ValueError("La rama indicada no cumple el formato permitido por GitHub.")
        return normalized

class GH001EvaluationRequest(GitHubBranchRequest):
    pass

class SourceResponse(BaseModel):
    type: str
    repository: str
    branch: str

class RuleResponse(BaseModel):
    id: str
    version: int

class EvidenceResponse(BaseModel):
    required_review_approvals: int | None
    dismiss_stale_reviews: bool | None
    hash: str

class EvaluationResponse(BaseModel):
    evaluation_id: str
    control_id: str
    rule: RuleResponse | None
    status: str
    source: SourceResponse
    evidence: EvidenceResponse
    collected_at: str
    evaluated_at: str

class GH002EvaluationRequest(GitHubRepositoryRequest):
    pass

class GH002EvidenceResponse(BaseModel):
    default_branch: str
    protection_enabled: bool | None
    hash: str

class GH002EvaluationResponse(BaseModel):
    evaluation_id: str
    control_id: str
    rule: RuleResponse | None
    status: str
    source: SourceResponse
    evidence: GH002EvidenceResponse
    collected_at: str
    evaluated_at: str


class GH003EvaluationRequest(GitHubBranchRequest):
    pass


class GH003EvidenceResponse(BaseModel):
    branch: str
    required_signatures_enabled: bool | None
    hash: str


class GH003EvaluationResponse(BaseModel):
    evaluation_id: str
    control_id: str
    rule: RuleResponse | None
    status: str
    source: SourceResponse
    evidence: GH003EvidenceResponse
    collected_at: str
    evaluated_at: str
