from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging

from securecode.application.evaluate_and_store import evaluate_and_store_gh001
from securecode.ports.evaluation_repository import EvaluationRepository
from securecode.api.schemas import (
    GH001EvaluationRequest,
    EvaluationResponse,
    SourceResponse,
    EvidenceResponse,
    RuleResponse
)
from securecode.api.dependencies import (
    get_db_session,
    get_evaluation_repository,
    get_github_token
)

app = FastAPI(
    title="SecureCode API",
    description="GH-001 Validation API",
    version="1.0.0"
)

logger = logging.getLogger(__name__)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/v1/evaluations/gh-001", response_model=EvaluationResponse)
def evaluate_gh001_endpoint(
    request: GH001EvaluationRequest,
    session: Session = Depends(get_db_session),
    github_token: str = Depends(get_github_token)
):
    """
    Executes the GH-001 control evaluation on a GitHub repository.
    """
    repo = PostgresEvaluationRepository_Dependency_Wrapper(session)
    
    try:
        persisted = evaluate_and_store_gh001(
            owner=request.owner,
            repo=request.repository,
            branch=request.branch,
            token=github_token,
            repository=repo
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail="Invalid evidence acquired") from e
    except RuntimeError as e:
        logger.error(f"Execution failed: {e}")
        raise HTTPException(status_code=502, detail="Infrastructure or upstream communication failure") from e
    except Exception as e:
        logger.error(f"Unexpected internal error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e
        
    rule_obj = None
    if persisted.rule_id is not None and persisted.rule_version is not None:
        rule_obj = RuleResponse(id=persisted.rule_id, version=persisted.rule_version)
        
    return EvaluationResponse(
        evaluation_id=str(persisted.id),
        control_id=persisted.control_id,
        rule=rule_obj,
        status=persisted.status.name,
        source=SourceResponse(
            type=persisted.source_type,
            repository=persisted.source_repository,
            branch=persisted.source_branch
        ),
        evidence=EvidenceResponse(
            required_review_approvals=persisted.reconstructed_evidence.required_review_approvals,
            dismiss_stale_reviews=persisted.reconstructed_evidence.dismiss_stale_reviews,
            hash=persisted.reconstructed_evidence.canonical_hash()
        ),
        collected_at=persisted.collected_at.isoformat(),
        evaluated_at=persisted.evaluated_at.isoformat()
    )

def PostgresEvaluationRepository_Dependency_Wrapper(session: Session) -> EvaluationRepository:
    from securecode.adapters.postgres.repository import PostgresEvaluationRepository
    return PostgresEvaluationRepository(session)

from securecode.application.evaluate_and_store import evaluate_and_store_gh002
from securecode.api.schemas import (
    GH002EvaluationRequest,
    GH002EvaluationResponse,
    GH002EvidenceResponse
)

@app.post("/api/v1/evaluations/gh-002", response_model=GH002EvaluationResponse)
def evaluate_gh002_endpoint(
    request: GH002EvaluationRequest,
    session: Session = Depends(get_db_session),
    github_token: str = Depends(get_github_token)
):
    """
    Executes the GH-002 control evaluation on a GitHub repository.
    """
    repo = PostgresEvaluationRepository_Dependency_Wrapper(session)
    
    try:
        persisted = evaluate_and_store_gh002(
            owner=request.owner,
            repo=request.repository,
            token=github_token,
            repository=repo
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail="Invalid evidence acquired") from e
    except RuntimeError as e:
        logger.error(f"Execution failed: {e}")
        raise HTTPException(status_code=502, detail="Infrastructure or upstream communication failure") from e
    except Exception as e:
        logger.error(f"Unexpected internal error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e
        
    rule_obj = None
    if persisted.rule_id is not None and persisted.rule_version is not None:
        rule_obj = RuleResponse(id=persisted.rule_id, version=persisted.rule_version)
        
    return GH002EvaluationResponse(
        evaluation_id=str(persisted.id),
        control_id=persisted.control_id,
        rule=rule_obj,
        status=persisted.status.name,
        source=SourceResponse(
            type=persisted.source_type,
            repository=persisted.source_repository,
            branch=persisted.source_branch
        ),
        evidence=GH002EvidenceResponse(
            default_branch=persisted.reconstructed_evidence.default_branch,
            protection_enabled=persisted.reconstructed_evidence.protection_enabled,
            hash=persisted.reconstructed_evidence.canonical_hash()
        ),
        collected_at=persisted.collected_at.isoformat(),
        evaluated_at=persisted.evaluated_at.isoformat()
    )
