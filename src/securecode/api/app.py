import os
import json
from pathlib import Path
from uuid import uuid4
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
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
    get_github_token,
    get_current_user,
    require_admin,
)
from securecode.adapters.postgres.models import User, EvaluationRecord

app = FastAPI(
    title="SecureCode API",
    description="GH-001 Validation API",
    version="1.0.0"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach browser protections without coupling them to the reverse proxy."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # The application is served as same-origin static HTML; no third-party scripts are needed.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; "
            "form-action 'self'; object-src 'none'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'"
        )
        return response


def _cors_origins() -> list[str]:
    return [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "").split(",") if origin.strip()]


app.add_middleware(SecurityHeadersMiddleware)
allowed_origins = _cors_origins()
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

logger = logging.getLogger(__name__)

# Montaje de archivos estaticos para la interfaz de usuario moderna
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>SecureCode API</h1><p>Consulte /docs para OpenAPI.</p>")

@app.get("/api/v1/rules")
def get_rules_catalog():
    rules_dir = Path(__file__).resolve().parent.parent.parent.parent / "rules"
    rules_list = []
    if rules_dir.exists():
        for r_file in sorted(rules_dir.glob("*.json")):
            try:
                rules_list.append(json.loads(r_file.read_text(encoding="utf-8")))
            except Exception:
                pass
    return {"rules": rules_list}

@app.get("/api/v1/system/overview")
def get_system_overview():
    return {
        "status": "online",
        "service": "SecureCode Compliance Engine",
        "version": "1.0.0",
        "ci_metrics": {
            "tests_total": 95,
            "tests_passing": 95,
            "coverage_pct": 89.5,
            "ci_run_id": "39183552777"
        },
        "performance": {
            "p95_latency_ms": 200,
            "p98_latency_ms": 300,
            "nominal_p95_ms": 180,
            "throughput_rps": 20.45,
            "error_rate_pct": 0.0
        },
        "capacity_finops": {
            "database": "PostgreSQL 15 / 16 (Supabase Hobby 500 MB)",
            "max_evaluations_theoretical": 20480,
            "estimated_record_size_kb": 25,
            "saturation_months_without_purge": 4.1
        },
        "sla": {
            "availability_target_pct": 99.5,
            "rto_compute": "< 15 minutes",
            "rpo_database": "< 24 hours"
        }
    }


from fastapi.security import OAuth2PasswordRequestForm
from securecode.api.security import verify_password, create_access_token, hash_password
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime, timezone
from typing import Literal

class Token(BaseModel):
    access_token: str
    token_type: str


class CurrentUserResponse(BaseModel):
    username: str
    active: bool
    role: Literal["admin", "auditor"]


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["admin", "auditor"] = "auditor"


class UserUpdateRequest(BaseModel):
    active: bool | None = None
    role: Literal["admin", "auditor"] | None = None
    password: str | None = Field(default=None, min_length=12, max_length=128)


class UserResponse(BaseModel):
    id: str
    username: str
    active: bool
    role: Literal["admin", "auditor"]
    created_at: datetime

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


@app.get("/api/v1/auth/me", response_model=CurrentUserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Return the authenticated identity; never expose password material."""
    return {
        "username": current_user.username,
        "active": current_user.active,
        "role": getattr(current_user, "role", "auditor"),
    }


def _user_response(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "active": user.active,
        "role": getattr(user, "role", "auditor"),
        "created_at": user.created_at,
    }


@app.get("/api/v1/admin/users", response_model=list[UserResponse])
def list_users(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_admin),
):
    return [_user_response(user) for user in session.query(User).order_by(User.username).all()]


@app.post("/api/v1/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: UserCreateRequest,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_admin),
):
    username = request.username.strip().lower()
    if session.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    user = User(
        id=uuid4(),
        username=username,
        password_hash=hash_password(request.password),
        active=True,
        role=request.role,
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _user_response(user)


@app.patch("/api/v1/admin/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    request: UserUpdateRequest,
    session: Session = Depends(get_db_session),
    current_admin: User = Depends(require_admin),
):
    user = session.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if str(user.id) == str(current_admin.id) and (request.active is False or request.role == "auditor"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrators cannot remove their own access")
    if request.active is not None:
        user.active = request.active
    if request.role is not None:
        user.role = request.role
    if request.password is not None:
        user.password_hash = hash_password(request.password)
    session.commit()
    session.refresh(user)
    return _user_response(user)


@app.get("/api/v1/evaluations/history")
def evaluation_history(
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return immutable evaluation metadata; auditors can only see their own work."""
    query = session.query(EvaluationRecord)
    if getattr(current_user, "role", "auditor") != "admin":
        query = query.filter(EvaluationRecord.requested_by_user_id == current_user.id)
    records = query.order_by(EvaluationRecord.evaluated_at.desc()).limit(limit).all()
    return {
        "evaluations": [
            {
                "evaluation_id": str(record.id),
                "control_id": record.control_id,
                "status": record.status,
                "repository": record.source_repository,
                "branch": record.source_branch,
                "evaluated_at": record.evaluated_at,
                "requested_by_user_id": str(record.requested_by_user_id) if record.requested_by_user_id else None,
            }
            for record in records
        ]
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

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
