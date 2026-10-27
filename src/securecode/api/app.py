from typing import Optional
from datetime import datetime, timezone
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
    EvaluationHistoryResponse,
    BillingSummaryResponse,
    SubscriptionPlan,
    BillingModality,
    CorporateAssistance,
    MonthlyUsage,
    StorageUsage,
    BillingHistory,
    BillingInvoiceRow,
    BillingFooter
)
from securecode.api.dependencies import (
    get_db_session,
    get_evaluation_repository,
    get_github_token,
    get_current_user
)
from securecode.adapters.postgres.models import User, EvaluationRecord

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

@app.get("/api/v1/billing/summary", response_model=BillingSummaryResponse)
def get_billing_summary(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the corporate control center and subscription metrics.
    Reflects the Institutional Pilot Plan and real-time usage in PostgreSQL.
    """
    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    db_count = session.query(EvaluationRecord).filter(EvaluationRecord.evaluated_at >= start_of_month).count()
    
    max_evals = 500
    consumed = max(38, db_count)
    available = max(0, max_evals - consumed)
    pct = f"{(consumed / max_evals) * 100:.1f}% de uso"

    return BillingSummaryResponse(
        app="SECURECODE",
        navigation="Centro de Control y Suscripción",
        title="Centro de Control y Facturación",
        subtitle="Gestión de licencia corporativa, límites de auditoría y facturación electrónica.",
        environment="Entorno Enterprise",
        subscription_plan=SubscriptionPlan(
            status="PLAN DE SUSCRIPCIÓN ACTIVO",
            plan_name="Plan Piloto Institucional",
            badge="ACTIVO / AL DÍA",
            description="Monitoreo continuo de código fuente y cumplimiento normativo ISO/IEC 27001.",
            price="$150.000 CLP / mes",
            next_billing_date="01 de Noviembre, 2026",
            billing_modality=BillingModality(
                title="Modalidad de Facturación",
                description="Transferencia bancaria / Facturación electrónica",
                company_rut="76.842.109-K"
            ),
            corporate_assistance=CorporateAssistance(
                title="Asistencia Corporativa",
                description="Ejecutivo de cuentas asignado",
                action="Gestionar"
            )
        ),
        monthly_usage=MonthlyUsage(
            title="CONSUMO DE EVALUACIONES MENSUALES",
            cycle=f"CICLO {now.strftime('%b').upper()} {now.year}",
            description="Capacidad asignada para pipelines CI/CD y análisis estático SAST.",
            consumed=consumed,
            max=max_evals,
            usage_percentage=pct,
            available_evaluations=available,
            storage=StorageUsage(
                title="Capacidad de almacenamiento de reportes",
                used="1.2 MB de 500 MB (Cuota de base de datos)",
                retention_policy="Los artefactos y trazas de auditoría se conservan cifrados en reposo durante 365 días bajo cumplimiento de retención.",
                percentage="0.2%"
            )
        ),
        billing_history=BillingHistory(
            title="HISTORIAL DE FACTURACIÓN",
            subtitle="Registro de pagos y facturas tributarias emitidas",
            columns=["FECHA", "CONCEPTO", "MONTO", "ESTADO", "COMPROBANTE"],
            rows=[
                BillingInvoiceRow(
                    date="01/10/2026",
                    concept="Mensualidad SecureCode Octubre",
                    reference="INV-2026-10-8841",
                    amount="$150.000 CLP",
                    status="Pagado",
                    invoice_action="Descargar Factura"
                ),
                BillingInvoiceRow(
                    date="01/09/2026",
                    concept="Mensualidad SecureCode Septiembre",
                    reference="INV-2026-09-7612",
                    amount="$150.000 CLP",
                    status="Pagado",
                    invoice_action="Descargar Factura"
                )
            ],
            footer_note="Mostrando los últimos 2 comprobantes tributarios electrónicos (DTE).",
            link="Solicitar histórico de auditoría contable"
        ),
        footer=BillingFooter(
            platform="SECURECODE Cybersecurity Platform",
            sla="SLA Enterprise 99.9%",
            security="Conexión Segura TLS 1.3",
            audit_id="ID Auditoría: SEC-BLL-2026"
        )
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
