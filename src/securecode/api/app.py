from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, status, Query
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
    RuleResponse,
    EvaluationHistoryItem,
    EvaluationHistoryResponse
)
from securecode.api.dependencies import (
    get_db_session,
    get_evaluation_repository,
    get_github_token,
    get_current_user
)
from securecode.adapters.postgres.models import User

app = FastAPI(
    title="SecureCode API",
    description="GH-001 Validation API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

from fastapi.security import OAuth2PasswordRequestForm
from securecode.api.security import verify_password, create_access_token
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

@app.post("/api/v1/auth/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_db_session)
):
    user = session.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/v1/evaluations", response_model=EvaluationHistoryResponse)
def list_evaluations_endpoint(
    status: Optional[str] = Query(None, description="Filter by status: PASS, FAIL, UNKNOWN"),
    search: Optional[str] = Query(None, description="Search term in repository, branch, control or hash"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    List historical evaluations persisted in PostgreSQL with filtering and search.
    """
    repo = PostgresEvaluationRepository_Dependency_Wrapper(session)
    filter_status = None if not status or status.upper() in ("TODOS", "ALL") else status.upper()
    total, records = repo.list_evaluations(
        status=filter_status,
        search=search,
        limit=limit,
        offset=offset
    )

    items = []
    for rec in records:
        branch_part = f" ({rec.source_branch})" if rec.source_branch and rec.source_branch.lower() != "unknown" else ""
        repo_and_branch = f"{rec.source_repository}{branch_part}"
        eval_id = f"eval_{str(rec.id)[:8]}"
        date_utc_str = rec.evaluated_at.strftime("%Y-%m-%d %H:%M")
        evidence_hash = rec.evidence.evidence_hash if rec.evidence else ""

        items.append(
            EvaluationHistoryItem(
                evaluation_id=eval_id,
                date_utc=date_utc_str,
                control=rec.control_id,
                repository_and_branch=repo_and_branch,
                verdict=rec.status,
                hash_sha256=evidence_hash,
                raw_id=str(rec.id),
                repository=rec.source_repository,
                branch=rec.source_branch or "",
                evaluated_at=rec.evaluated_at.isoformat()
            )
        )

    pagination_info = f"Mostrando {len(items)} de {total} registros"
    return EvaluationHistoryResponse(
        total=total,
        items=items,
        pagination_info=pagination_info
    )

@app.post("/api/v1/evaluations/gh-001", response_model=EvaluationResponse)
def evaluate_gh001_endpoint(
    request: GH001EvaluationRequest,
    session: Session = Depends(get_db_session),
    github_token: str = Depends(get_github_token),
    current_user: User = Depends(get_current_user)
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
            repository=repo,
            requested_by_user_id=current_user.id
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
    github_token: str = Depends(get_github_token),
    current_user: User = Depends(get_current_user)
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
            repository=repo,
            requested_by_user_id=current_user.id
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
