import hashlib
import json
import logging
import os
import re
from pathlib import Path
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from securecode.adapters.postgres.models import (
    EnterpriseTrialRepository,
    EnterpriseTrialUsage,
    EvaluationRecord,
    LoginAttempt,
    Organization,
    RepositoryAuthorization,
    SubscriptionEvent,
    User,
    UserAuditEvent,
    UserFinOpsSettings,
    UserSettings,
    UserSubscription,
)
from securecode.api.dependencies import (
    get_current_user,
    get_db_session,
    get_github_token,
    require_admin,
)
from securecode.api.schemas import (
    EvaluationResponse,
    EvidenceResponse,
    GH001EvaluationRequest,
    RuleResponse,
    SourceResponse,
)
from securecode.application.enterprise_trial import (
    TrialPolicyError,
    complete_evaluation_reservation,
    create_trial,
    get_active_trial_for_user,
    get_trial_for_user,
    is_trial_owner,
    release_evaluation_reservation,
    reserve_evaluation,
)
from securecode.application.enterprise_trial import (
    authorize_repository as authorize_trial_repository,
)
from securecode.application.evaluate_and_store import evaluate_and_store_gh001
from securecode.engine.evaluator import get_rules_directory
from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence
from securecode.ports.evaluation_repository import EvaluationRepository

app = FastAPI(
    title="SecureCode API",
    description="API de evaluación de controles GitHub GH-001, GH-002 y GH-003, con administración, auditoría y FinOps.",
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
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )

logger = logging.getLogger(__name__)

# Montaje de archivos estaticos para la interfaz de usuario moderna
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    """Serve the application shell without caching role-sensitive navigation."""
    no_store_headers = {"Cache-Control": "no-store, max-age=0"}
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"), headers=no_store_headers)
    return HTMLResponse(
        content="<h1>SecureCode API</h1><p>Consulte /docs para OpenAPI.</p>", headers=no_store_headers
    )

@app.get("/api/v1/rules")
def get_rules_catalog():
    """Publish only the canonical rule catalog used by the evaluator UI.

    The client consumes this endpoint to avoid claiming controls that are not
    actually present in the deployed rule set.
    """
    rules_dir = get_rules_directory()
    rules_list = []
    if rules_dir.exists():
        for r_file in sorted(rules_dir.glob("*.json")):
            try:
                rules_list.append(json.loads(r_file.read_text(encoding="utf-8")))
            except Exception:
                pass
    return {
        "rules": rules_list,
        "active_controls": len(rules_list),
        "catalog_version": "1",
    }

@app.get("/api/v1/system/overview")
def get_system_overview(_: User = Depends(require_admin)):
    """Administrative status only; CI and billing are not live telemetry sources."""
    return {
        "status": "online",
        "service": "SecureCode Compliance Engine",
        "version": "1.0.0",
        "ci_metrics": {
            "measurement_state": "not_connected",
            "note": "Consulta GitHub Actions para resultados y cobertura vigentes.",
        },
        "performance": {
            "measurement_state": "not_live",
            "scope": "Las métricas de rendimiento se documentan como pruebas controladas, no como telemetría de producción.",
            "p95_latency_ms": None,
            "throughput_rps": None,
        },
        "capacity_finops": {"measurement_state": "not_connected"},
        "sla": {
            "availability_target_pct": 99.5,
            "rto_compute": "< 15 minutes",
            "rpo_database": "< 24 hours"
        }
    }


from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from securecode.api.security import create_access_token, hash_password, verify_password

# Equalize the expensive password-verification path for unknown usernames.
# This reduces timing-based account enumeration without persisting a fake user.
_DUMMY_PASSWORD_HASH = hash_password("securecode-login-timing-placeholder")

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
    updated_at: datetime | None = None
    last_login_at: datetime | None = None


class UserAuditEventResponse(BaseModel):
    id: str
    action: str
    actor_username: str | None = None
    target_username: str | None = None
    details: dict
    created_at: datetime


class RepositoryAuthorizationRequest(BaseModel):
    user_id: UUID
    repository: str = Field(min_length=3, max_length=201)


class RepositoryAuthorizationUpdateRequest(BaseModel):
    active: bool


class RepositoryAuthorizationResponse(BaseModel):
    id: str
    user_id: str
    username: str | None = None
    repository: str
    active: bool
    created_at: datetime
    updated_at: datetime


class ClientSettingsUpdateRequest(BaseModel):
    default_repository: str | None = Field(default=None, max_length=200)
    default_branch: str | None = Field(default=None, min_length=1, max_length=255)
    locale: Literal["es-CL", "en-US"] | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    theme: Literal["system", "light", "dark"] | None = None
    notify_evaluation_completed: bool | None = None
    notify_evaluation_failure: bool | None = None
    notify_weekly_digest: bool | None = None


class ClientSettingsResponse(BaseModel):
    default_repository: str | None
    default_branch: str
    locale: Literal["es-CL", "en-US"]
    timezone: str
    theme: Literal["system", "light", "dark"]
    notify_evaluation_completed: bool
    notify_evaluation_failure: bool
    notify_weekly_digest: bool
    updated_at: datetime | None = None


class SubscriptionChangeRequest(BaseModel):
    plan_id: Literal["pro", "premium"]
    confirmation: bool = False


class SubscriptionEventResponse(BaseModel):
    id: str
    previous_plan_id: str | None
    new_plan_id: str
    occurred_at: datetime
    effective_from: datetime
    effective_until: datetime
    event_type: str


class SubscriptionResponse(BaseModel):
    plan_id: Literal["pro", "premium"]
    started_at: datetime
    expires_at: datetime
    last_changed_at: datetime
    can_change: bool
    next_change_at: datetime
    billing_mode: Literal["demo_non_billable"]
    catalog: list[dict]


class FinOpsSettingsUpdateRequest(BaseModel):
    budget_clp: Literal[10, 50, 100, 200, 500, 1000]
    alert_threshold_pct: Literal[50, 80, 100]
    alert_enabled: bool


class FinOpsResponse(BaseModel):
    scope: Literal["account", "platform"]
    period_start: datetime
    evaluations_current_period: int
    evaluations_all_time: int
    budget_clp: int
    alert_threshold_pct: int
    alert_enabled: bool
    billing_data_state: Literal["not_connected"]
    observed_spend_clp: None = None
    updated_at: datetime | None = None


class EnterpriseTrialActivationRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    confirmation: bool = False


class EnterpriseTrialRepositoryRequest(BaseModel):
    repository: str = Field(min_length=3, max_length=201)


class EnterpriseTrialResponse(BaseModel):
    available: bool
    status: Literal["not_started", "active", "expired"]
    organization_name: str | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    repository_limit: int | None = None
    repositories_used: int = 0
    repositories_remaining: int = 0
    evaluation_limit: int | None = None
    evaluations_used: int = 0
    evaluations_remaining: int = 0
    repositories: list[str] = []
    billing_mode: Literal["trial_non_billable"] = "trial_non_billable"


_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_SUBSCRIPTION_PERIOD = timedelta(days=30)
_PLAN_CATALOG = {
    "pro": {
        "id": "pro",
        "name": "Pro",
        "price_clp": 150025,
        "features": ["3 controles canónicos", "Evidencia SHA-256", "Historial y exportación CSV"],
    },
    "premium": {
        "id": "premium",
        "name": "Premium",
        "price_clp": 375064,
        "features": ["Todo lo incluido en Pro", "Capacidad ampliada según contrato", "Soporte prioritario según contrato"],
    },
}


def _bounded_int_from_environment(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        return min(max(int(os.environ.get(name, str(default))), minimum), maximum)
    except ValueError:
        return default


def _login_rate_limit_settings() -> tuple[int, int]:
    return (
        _bounded_int_from_environment("LOGIN_MAX_FAILURES", 5, 1, 20),
        _bounded_int_from_environment("LOGIN_WINDOW_SECONDS", 900, 60, 86_400),
    )


def _login_scope_hash(username: str, request: Request) -> str:
    """Hash a username/client tuple without persisting personal identifiers."""
    client = request.client.host if request.client else "unknown"
    if os.environ.get("TRUST_PROXY_HEADERS", "false").lower() == "true":
        client = request.headers.get("x-forwarded-for", client).split(",", 1)[0].strip()
    return hashlib.sha256(f"{username}\x00{client}".encode()).hexdigest()


def _as_utc(value: datetime) -> datetime:
    """Normalize drivers such as SQLite that return naive timezone columns."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _login_retry_after(session: Session, scope_hash: str, now: datetime) -> int | None:
    attempt = session.query(LoginAttempt).filter(LoginAttempt.scope_hash == scope_hash).first()
    if attempt and attempt.locked_until and _as_utc(attempt.locked_until) > now:
        return max(1, int((_as_utc(attempt.locked_until) - now).total_seconds()))
    return None


def _record_failed_login(session: Session, scope_hash: str, now: datetime) -> None:
    maximum_failures, window_seconds = _login_rate_limit_settings()
    attempt = session.query(LoginAttempt).filter(LoginAttempt.scope_hash == scope_hash).first()
    if attempt is None:
        attempt = LoginAttempt(scope_hash=scope_hash, failure_count=1, window_started_at=now, locked_until=None, updated_at=now)
        session.add(attempt)
    elif (now - _as_utc(attempt.window_started_at)).total_seconds() >= window_seconds:
        attempt.failure_count, attempt.window_started_at, attempt.locked_until = 1, now, None
        attempt.updated_at = now
    else:
        attempt.failure_count += 1
        attempt.updated_at = now
    if attempt.failure_count >= maximum_failures:
        attempt.locked_until = now + timedelta(seconds=window_seconds)
    session.commit()


def _clear_failed_logins(session: Session, scope_hash: str) -> None:
    attempt = session.query(LoginAttempt).filter(LoginAttempt.scope_hash == scope_hash).first()
    if attempt is not None:
        session.delete(attempt)


def _normalise_username(value: str) -> str:
    username = value.strip().lower()
    if not _EMAIL_PATTERN.fullmatch(username):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="El usuario debe ser un correo electrónico válido")
    return username


def _normalise_repository(value: str) -> str:
    repository = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", repository):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="El repositorio debe usar el formato owner/repo")
    # GitHub identifica owner y repository sin distinguir mayúsculas.  Canonicalizar
    # evita que ``Acme/App`` y ``acme/app`` creen alcances distintos por accidente.
    return repository.lower()


def _require_repository_authorization(session: Session, current_user: User, owner: str, repository: str) -> None:
    """Auditors require account scope or an active trial's explicit scope."""
    if getattr(current_user, "role", "auditor") == "admin":
        return
    canonical = _normalise_repository(f"{owner}/{repository}")
    authorization = session.query(RepositoryAuthorization).filter(
        RepositoryAuthorization.user_id == current_user.id,
        func.lower(RepositoryAuthorization.repository) == canonical,
        RepositoryAuthorization.active.is_(True),
    ).first()
    if authorization is None:
        trial = get_active_trial_for_user(session, current_user.id)
        trial_scope = None
        if trial is not None:
            trial_scope = (
                session.query(EnterpriseTrialRepository)
                .filter_by(trial_id=trial.id, repository=canonical)
                .first()
            )
        if trial_scope is not None:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta no está autorizada para evaluar este repositorio. Solicita acceso a un administrador.",
        )


def _validate_password_strength(password: str) -> None:
    if not (len(password) >= 12 and re.search(r"[a-z]", password) and re.search(r"[A-Z]", password) and re.search(r"\d", password) and re.search(r"[^A-Za-z0-9]", password)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La contraseña debe tener 12+ caracteres, mayúscula, minúscula, número y símbolo",
        )


def _record_user_audit(session: Session, actor_id: UUID | None, target_id: UUID | None, action: str, details: dict) -> None:
    """Record account lifecycle changes without persisting credentials or tokens."""
    session.add(UserAuditEvent(
        id=uuid4(), actor_user_id=actor_id, target_user_id=target_id,
        action=action, details=details, created_at=datetime.now(UTC),
    ))


def _settings_response(settings: UserSettings | None) -> dict:
    """Produce safe defaults even before a user saves preferences for the first time."""
    if settings is None:
        return {
            "default_repository": None, "default_branch": "main", "locale": "es-CL",
            "timezone": "America/Santiago", "theme": "system",
            "notify_evaluation_completed": True, "notify_evaluation_failure": True,
            "notify_weekly_digest": False, "updated_at": None,
        }
    return {
        "default_repository": settings.default_repository, "default_branch": settings.default_branch,
        "locale": settings.locale, "timezone": settings.timezone, "theme": settings.theme,
        "notify_evaluation_completed": settings.notify_evaluation_completed,
        "notify_evaluation_failure": settings.notify_evaluation_failure,
        "notify_weekly_digest": settings.notify_weekly_digest, "updated_at": settings.updated_at,
    }


def _ensure_subscription(session: Session, user_id: UUID) -> UserSubscription:
    subscription = session.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    if subscription:
        return subscription
    now = datetime.now(UTC)
    subscription = UserSubscription(
        user_id=user_id, plan_id="pro", started_at=now,
        expires_at=now + _SUBSCRIPTION_PERIOD, last_changed_at=now,
    )
    session.add(subscription)
    session.add(SubscriptionEvent(
        id=uuid4(), user_id=user_id, previous_plan_id=None, new_plan_id="pro",
        occurred_at=now, effective_from=now, effective_until=subscription.expires_at,
        event_type="initialized",
    ))
    session.commit()
    session.refresh(subscription)
    return subscription


def _subscription_response(subscription: UserSubscription) -> dict:
    started_at = _as_utc(subscription.started_at)
    expires_at = _as_utc(subscription.expires_at)
    last_changed_at = _as_utc(subscription.last_changed_at)
    next_change_at = last_changed_at + _SUBSCRIPTION_PERIOD
    return {
        "plan_id": subscription.plan_id,
        "started_at": started_at,
        "expires_at": expires_at,
        "last_changed_at": last_changed_at,
        "can_change": datetime.now(UTC) >= next_change_at,
        "next_change_at": next_change_at,
        "billing_mode": "demo_non_billable",
        "catalog": list(_PLAN_CATALOG.values()),
    }


def _ensure_finops_settings(session: Session, user_id: UUID) -> UserFinOpsSettings:
    settings = session.query(UserFinOpsSettings).filter(UserFinOpsSettings.user_id == user_id).first()
    if settings:
        return settings
    settings = UserFinOpsSettings(user_id=user_id, budget_clp=1000, alert_threshold_pct=80, alert_enabled=True)
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def _period_start_utc(now: datetime | None = None) -> datetime:
    current = now or datetime.now(UTC)
    return current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _finops_response(session: Session, current_user: User, settings: UserFinOpsSettings) -> dict:
    query = session.query(EvaluationRecord)
    scope = "platform" if getattr(current_user, "role", "auditor") == "admin" else "account"
    if scope == "account":
        query = query.filter(EvaluationRecord.requested_by_user_id == current_user.id)
    period_start = _period_start_utc()
    all_time = query.count()
    period_count = query.filter(EvaluationRecord.evaluated_at >= period_start).count()
    return {
        "scope": scope, "period_start": period_start,
        "evaluations_current_period": period_count, "evaluations_all_time": all_time,
        "budget_clp": settings.budget_clp, "alert_threshold_pct": settings.alert_threshold_pct,
        "alert_enabled": settings.alert_enabled, "billing_data_state": "not_connected",
        "observed_spend_clp": None, "updated_at": settings.updated_at,
    }


def _trial_response(session: Session, current_user: User) -> dict:
    """Return entitlement state without presenting a trial as a paid plan."""
    trial = get_trial_for_user(session, current_user.id)
    if trial is None:
        return {
            "available": True, "status": "not_started", "organization_name": None,
            "starts_at": None, "expires_at": None, "repository_limit": None,
            "repositories_used": 0, "repositories_remaining": 0,
            "evaluation_limit": None, "evaluations_used": 0, "evaluations_remaining": 0,
            "repositories": [], "billing_mode": "trial_non_billable",
        }
    repositories = (
        session.query(EnterpriseTrialRepository)
        .filter(EnterpriseTrialRepository.trial_id == trial.id)
        .order_by(EnterpriseTrialRepository.repository.asc())
        .all()
    )
    usage_count = (
        session.query(EnterpriseTrialUsage)
        .filter(
            EnterpriseTrialUsage.trial_id == trial.id,
            EnterpriseTrialUsage.state.in_(("reserved", "completed")),
        )
        .count()
    )
    organization = session.query(Organization).filter(Organization.id == trial.organization_id).first()
    active = get_active_trial_for_user(session, current_user.id) is not None
    return {
        "available": False,
        "status": "active" if active else "expired",
        "organization_name": organization.name if organization else None,
        "starts_at": _as_utc(trial.starts_at), "expires_at": _as_utc(trial.expires_at),
        "repository_limit": trial.repository_limit, "repositories_used": len(repositories),
        "repositories_remaining": max(0, trial.repository_limit - len(repositories)),
        "evaluation_limit": trial.evaluation_limit, "evaluations_used": usage_count,
        "evaluations_remaining": max(0, trial.evaluation_limit - usage_count),
        "repositories": [item.repository for item in repositories],
        "billing_mode": "trial_non_billable",
    }

@app.post("/api/v1/auth/token", response_model=Token)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_db_session)
):
    normalized_username = form_data.username.strip().lower()
    scope_hash = _login_scope_hash(normalized_username, request)
    now = datetime.now(UTC)
    retry_after = _login_retry_after(session, scope_hash, now)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    user = session.query(User).filter(User.username == normalized_username).first()
    password_valid = verify_password(form_data.password, user.password_hash if user else _DUMMY_PASSWORD_HASH)
    if not user or not password_valid:
        _record_failed_login(session, scope_hash, now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.active:
        _record_failed_login(session, scope_hash, now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Last-login metadata is operational, never used as an authorization decision.
    user.last_login_at = datetime.now(UTC)
    _clear_failed_logins(session, scope_hash)
    if hasattr(session, "commit"):
        try:
            session.commit()
        except Exception:
            if hasattr(session, "rollback"):
                session.rollback()
            logger.warning("Could not update last_login_at for authenticated user")

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


@app.get("/api/v1/settings", response_model=ClientSettingsResponse)
def get_client_settings(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's own non-sensitive preferences."""
    settings = session.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    return _settings_response(settings)


@app.patch("/api/v1/settings", response_model=ClientSettingsResponse)
def update_client_settings(
    request: ClientSettingsUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Persist user preferences without exposing integration credentials or changing canonical rules."""
    incoming = request.model_dump(exclude_unset=True)
    if not incoming:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="No se recibió ninguna preferencia para actualizar")

    repository = incoming.get("default_repository")
    if repository is not None:
        repository = repository.strip()
        if repository and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", repository):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="El repositorio debe usar el formato owner/repo")
        incoming["default_repository"] = repository or None

    branch = incoming.get("default_branch")
    if branch is not None:
        branch = branch.strip()
        if not branch or any(character.isspace() for character in branch):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="La rama no puede estar vacía ni contener espacios")
        incoming["default_branch"] = branch

    timezone_name = incoming.get("timezone")
    if timezone_name is not None:
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="La zona horaria indicada no es válida") from error

    settings = session.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if settings is None:
        settings = UserSettings(user_id=current_user.id)
        session.add(settings)
    changes: dict[str, object] = {}
    for field, value in incoming.items():
        previous = getattr(settings, field)
        if previous != value:
            changes[field] = {"from": previous, "to": value}
            setattr(settings, field, value)
    if not changes:
        return _settings_response(settings)
    settings.updated_at = datetime.now(UTC)
    _record_user_audit(session, current_user.id, current_user.id, "client_settings_updated", changes)
    session.commit()
    session.refresh(settings)
    return _settings_response(settings)


@app.get("/api/v1/subscription", response_model=SubscriptionResponse)
def get_subscription(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated account's current 30-day demo subscription."""
    return _subscription_response(_ensure_subscription(session, current_user.id))


@app.patch("/api/v1/subscription", response_model=SubscriptionResponse)
def change_subscription(
    request: SubscriptionChangeRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Confirm one subscription change per 30-day period; this endpoint never bills."""
    if not request.confirmation:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Debes confirmar el cambio de plan")
    subscription = _ensure_subscription(session, current_user.id)
    if request.plan_id == subscription.plan_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="El plan seleccionado ya está activo")
    now = datetime.now(UTC)
    next_change_at = _as_utc(subscription.last_changed_at) + _SUBSCRIPTION_PERIOD
    if now < next_change_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El próximo cambio estará disponible el {next_change_at.isoformat()}",
        )
    previous_plan_id = subscription.plan_id
    subscription.plan_id = request.plan_id
    subscription.started_at = now
    subscription.expires_at = now + _SUBSCRIPTION_PERIOD
    subscription.last_changed_at = now
    session.add(SubscriptionEvent(
        id=uuid4(), user_id=current_user.id, previous_plan_id=previous_plan_id,
        new_plan_id=request.plan_id, occurred_at=now, effective_from=subscription.started_at,
        effective_until=subscription.expires_at, event_type="plan_changed",
    ))
    _record_user_audit(session, current_user.id, current_user.id, "subscription_changed", {
        "from": previous_plan_id, "to": request.plan_id, "billing_mode": "demo_non_billable",
    })
    session.commit()
    session.refresh(subscription)
    return _subscription_response(subscription)


@app.get("/api/v1/subscription/history", response_model=list[SubscriptionEventResponse])
def subscription_history(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """List only the current user's confirmed subscription lifecycle events."""
    events = (
        session.query(SubscriptionEvent)
        .filter(SubscriptionEvent.user_id == current_user.id)
        .order_by(SubscriptionEvent.occurred_at.desc())
        .limit(limit)
        .all()
    )
    return [{
        "id": str(event.id), "previous_plan_id": event.previous_plan_id,
        "new_plan_id": event.new_plan_id, "occurred_at": event.occurred_at,
        "effective_from": event.effective_from, "effective_until": event.effective_until,
        "event_type": event.event_type,
    } for event in events]


@app.get("/api/v1/finops", response_model=FinOpsResponse)
def get_finops(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return measurable evaluation consumption and non-billable FinOps preferences."""
    settings = _ensure_finops_settings(session, current_user.id)
    return _finops_response(session, current_user, settings)


@app.patch("/api/v1/finops", response_model=FinOpsResponse)
def update_finops(
    request: FinOpsSettingsUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Persist alert preferences; never imply a connection to Cloud Billing."""
    settings = _ensure_finops_settings(session, current_user.id)
    changes: dict[str, object] = {}
    for field, value in request.model_dump().items():
        previous = getattr(settings, field)
        if previous != value:
            changes[field] = {"from": previous, "to": value}
            setattr(settings, field, value)
    if changes:
        settings.updated_at = datetime.now(UTC)
        _record_user_audit(session, current_user.id, current_user.id, "finops_preferences_updated", changes)
        session.commit()
        session.refresh(settings)
    return _finops_response(session, current_user, settings)


@app.get("/api/v1/enterprise-trial", response_model=EnterpriseTrialResponse)
def get_enterprise_trial(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Expose only the caller's non-billable, one-time Enterprise Trial state."""
    return _trial_response(session, current_user)


@app.post("/api/v1/enterprise-trial", response_model=EnterpriseTrialResponse, status_code=status.HTTP_201_CREATED)
def activate_enterprise_trial(
    request: EnterpriseTrialActivationRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Activate one 14-day technical trial after explicit confirmation.

    The entitlement contains no payment operation, price, invoice, or renewal.
    A user who has started a trial cannot create another one after it expires.
    """
    if not request.confirmation:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Debes confirmar la activación del trial")
    if get_trial_for_user(session, current_user.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta cuenta ya utilizó su Enterprise Trial")
    try:
        trial = create_trial(
            session,
            organization_name=request.organization_name,
            owner_user_id=current_user.id,
        )
        _record_user_audit(session, current_user.id, current_user.id, "enterprise_trial_activated", {
            "trial_id": str(trial.id), "billing_mode": "trial_non_billable",
        })
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _trial_response(session, current_user)


@app.post("/api/v1/enterprise-trial/repositories", response_model=EnterpriseTrialResponse)
def add_enterprise_trial_repository(
    request: EnterpriseTrialRepositoryRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Authorize a repository in the caller's active trial, up to its fixed quota."""
    trial = get_active_trial_for_user(session, current_user.id)
    if trial is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No hay un Enterprise Trial activo")
    if not is_trial_owner(session, trial_id=trial.id, user_id=current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el propietario del trial puede agregar repositorios")
    try:
        repository = _normalise_repository(request.repository)
        authorize_trial_repository(session, trial_id=trial.id, repository=repository)
        _record_user_audit(session, current_user.id, current_user.id, "enterprise_trial_repository_authorized", {
            "trial_id": str(trial.id), "repository": repository,
        })
        session.commit()
    except (TrialPolicyError, ValueError) as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return _trial_response(session, current_user)


def _reserve_trial_evaluation(
    session: Session,
    current_user: User,
    repository: str,
    idempotency_key: str | None,
) -> UUID | None:
    """Reserve quota only for an active trial, before contacting GitHub.

    Normal subscriptions are unchanged. A trial request must provide an
    idempotency key because a client retry must never consume another unit.
    """
    trial = get_active_trial_for_user(session, current_user.id)
    if trial is None:
        return None
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key es obligatorio durante un Enterprise Trial activo",
        )
    existing = (
        session.query(EnterpriseTrialUsage)
        .filter_by(trial_id=trial.id, idempotency_key=idempotency_key)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta solicitud de trial ya fue procesada o está en curso",
        )
    try:
        reservation = reserve_evaluation(
            session,
            trial_id=trial.id,
            repository=repository,
            idempotency_key=idempotency_key,
        )
        session.commit()
        return reservation.id
    except (TrialPolicyError, ValueError) as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


def _complete_trial_evaluation(session: Session, reservation_id: UUID | None, evaluation_id: UUID) -> None:
    if reservation_id is None:
        return
    complete_evaluation_reservation(session, usage_id=reservation_id, evaluation_id=evaluation_id)
    session.commit()


def _release_trial_evaluation(session: Session, reservation_id: UUID | None) -> None:
    if reservation_id is None:
        return
    try:
        release_evaluation_reservation(session, usage_id=reservation_id)
        session.commit()
    except SQLAlchemyError:  # Best-effort cleanup after an upstream evaluation failure.
        session.rollback()
        logger.exception("Could not release Enterprise Trial reservation")


def _user_response(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "active": user.active,
        "role": getattr(user, "role", "auditor"),
        "created_at": user.created_at,
        "updated_at": getattr(user, "updated_at", user.created_at),
        "last_login_at": getattr(user, "last_login_at", None),
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
    username = _normalise_username(request.username)
    _validate_password_strength(request.password)
    if session.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    user = User(
        id=uuid4(),
        username=username,
        password_hash=hash_password(request.password),
        active=True,
        role=request.role,
        created_at=datetime.now(UTC),
    )
    session.add(user)
    _record_user_audit(session, _.id, user.id, "account_created", {"role": user.role, "active": True})
    session.commit()
    session.refresh(user)
    return _user_response(user)


@app.patch("/api/v1/admin/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    session: Session = Depends(get_db_session),
    current_admin: User = Depends(require_admin),
):
    user = session.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if str(user.id) == str(current_admin.id) and (request.active is False or request.role == "auditor"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrators cannot remove their own access")
    removes_admin_access = user.role == "admin" and user.active and (request.active is False or request.role == "auditor")
    if removes_admin_access:
        active_admins = session.query(User).filter(User.role == "admin", User.active.is_(True)).count()
        if active_admins <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe existir al menos un administrador activo")
    changes: dict[str, object] = {}
    if request.active is not None:
        if user.active != request.active:
            changes["active"] = {"from": user.active, "to": request.active}
        user.active = request.active
    if request.role is not None:
        if user.role != request.role:
            changes["role"] = {"from": user.role, "to": request.role}
        user.role = request.role
    if request.password is not None:
        _validate_password_strength(request.password)
        user.password_hash = hash_password(request.password)
        changes["password_reset"] = True
    if not changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="No se recibió ningún cambio para aplicar")
    user.updated_at = datetime.now(UTC)
    _record_user_audit(session, current_admin.id, user.id, "account_updated", changes)
    session.commit()
    session.refresh(user)
    return _user_response(user)


@app.get("/api/v1/admin/user-audit-events", response_model=list[UserAuditEventResponse])
def list_user_audit_events(
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_db_session),
    _: User = Depends(require_admin),
):
    """Expose an administrator-only, credential-free account audit trail."""
    events = session.query(UserAuditEvent).order_by(UserAuditEvent.created_at.desc()).limit(limit).all()
    user_ids = {event.actor_user_id for event in events if event.actor_user_id} | {event.target_user_id for event in events if event.target_user_id}
    users = session.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    usernames = {user.id: user.username for user in users}
    return [{
        "id": str(event.id), "action": event.action,
        "actor_username": usernames.get(event.actor_user_id) if event.actor_user_id else None,
        "target_username": usernames.get(event.target_user_id) if event.target_user_id else None,
        "details": event.details, "created_at": event.created_at,
    } for event in events]


def _repository_authorization_response(authorization: RepositoryAuthorization, username: str | None = None) -> dict:
    return {
        "id": str(authorization.id), "user_id": str(authorization.user_id), "username": username,
        "repository": authorization.repository, "active": authorization.active,
        "created_at": authorization.created_at, "updated_at": authorization.updated_at,
    }


@app.get("/api/v1/admin/repository-authorizations", response_model=list[RepositoryAuthorizationResponse])
def list_repository_authorizations(
    user_id: UUID | None = None,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_admin),
):
    query = session.query(RepositoryAuthorization)
    if user_id is not None:
        query = query.filter(RepositoryAuthorization.user_id == user_id)
    authorizations = query.order_by(RepositoryAuthorization.repository).all()
    user_ids = {item.user_id for item in authorizations}
    users = session.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    usernames = {user.id: user.username for user in users}
    return [_repository_authorization_response(item, usernames.get(item.user_id)) for item in authorizations]


@app.post("/api/v1/admin/repository-authorizations", response_model=RepositoryAuthorizationResponse, status_code=status.HTTP_201_CREATED)
def create_repository_authorization(
    request: RepositoryAuthorizationRequest,
    session: Session = Depends(get_db_session),
    current_admin: User = Depends(require_admin),
):
    target_user = session.query(User).filter(User.id == request.user_id).first()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    repository = _normalise_repository(request.repository)
    existing = session.query(RepositoryAuthorization).filter(
        RepositoryAuthorization.user_id == request.user_id,
        func.lower(RepositoryAuthorization.repository) == repository,
    ).first()
    if existing is not None:
        if existing.active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El repositorio ya está autorizado para esta cuenta")
        existing.active = True
        existing.updated_at = datetime.now(UTC)
        action = "repository_authorization_reactivated"
        authorization = existing
    else:
        authorization = RepositoryAuthorization(
            id=uuid4(), user_id=request.user_id, repository=repository, active=True,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        session.add(authorization)
        action = "repository_authorization_created"
    _record_user_audit(session, current_admin.id, target_user.id, action, {"repository": repository})
    session.commit()
    session.refresh(authorization)
    return _repository_authorization_response(authorization, target_user.username)


@app.patch("/api/v1/admin/repository-authorizations/{authorization_id}", response_model=RepositoryAuthorizationResponse)
def update_repository_authorization(
    authorization_id: UUID,
    request: RepositoryAuthorizationUpdateRequest,
    session: Session = Depends(get_db_session),
    current_admin: User = Depends(require_admin),
):
    authorization = session.query(RepositoryAuthorization).filter(RepositoryAuthorization.id == authorization_id).first()
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository authorization not found")
    if authorization.active == request.active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="No se recibió ningún cambio para aplicar")
    authorization.active = request.active
    authorization.updated_at = datetime.now(UTC)
    _record_user_audit(session, current_admin.id, authorization.user_id, "repository_authorization_updated", {
        "repository": authorization.repository, "active": request.active,
    })
    session.commit()
    session.refresh(authorization)
    user = session.query(User).filter(User.id == authorization.user_id).first()
    return _repository_authorization_response(authorization, user.username if user else None)


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


@app.get("/api/v1/evaluations/{evaluation_id}")
def evaluation_detail(
    evaluation_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return the immutable evidence for one evaluation, subject to ownership."""
    record = session.query(EvaluationRecord).filter(EvaluationRecord.id == evaluation_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    is_admin = getattr(current_user, "role", "auditor") == "admin"
    if not is_admin and record.requested_by_user_id != current_user.id:
        # Do not disclose the existence of another auditor's evaluation.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    persisted = PostgresEvaluationRepository_Dependency_Wrapper(session).get_evaluation(evaluation_id)
    if not persisted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    reconstructed = persisted.reconstructed_evidence
    evidence: dict[str, object]
    if persisted.control_id == "GH-001" and isinstance(reconstructed, GH001Evidence):
        evidence = {
            "required_review_approvals": reconstructed.required_review_approvals,
            "dismiss_stale_reviews": reconstructed.dismiss_stale_reviews,
        }
    elif persisted.control_id == "GH-002" and isinstance(reconstructed, GH002Evidence):
        evidence = {
            "default_branch": reconstructed.default_branch,
            "protection_enabled": reconstructed.protection_enabled,
        }
    elif persisted.control_id == "GH-003" and isinstance(reconstructed, GH003Evidence):
        evidence = {
            "branch": reconstructed.branch,
            "required_signatures_enabled": reconstructed.required_signatures_enabled,
        }
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored evaluation evidence is inconsistent")

    evidence["hash"] = reconstructed.canonical_hash()
    return {
        "evaluation_id": str(persisted.id),
        "control_id": persisted.control_id,
        "rule": (
            {"id": persisted.rule_id, "version": persisted.rule_version}
            if persisted.rule_id is not None and persisted.rule_version is not None
            else None
        ),
        "status": persisted.status.name,
        "source": {
            "type": persisted.source_type,
            "repository": persisted.source_repository,
            "branch": persisted.source_branch,
        },
        "evidence": evidence,
        "collected_at": persisted.collected_at.isoformat(),
        "evaluated_at": persisted.evaluated_at.isoformat(),
    }


@app.get("/api/v1/verify/{evaluation_id}")
def verify_evidence_public(
    evaluation_id: UUID,
    session: Session = Depends(get_db_session),
):
    """Publicly verify integrity without disclosing repository or user data."""
    record = session.query(EvaluationRecord).filter(EvaluationRecord.id == evaluation_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    persisted = PostgresEvaluationRepository_Dependency_Wrapper(session).get_evaluation(evaluation_id)
    if not persisted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    computed_hash = persisted.reconstructed_evidence.canonical_hash()
    return {
        "evaluation_id": str(persisted.id),
        "control_id": persisted.control_id,
        "status": persisted.status.name,
        "evidence_hash": record.evidence.evidence_hash,
        "integrity_valid": record.evidence.evidence_hash == computed_hash,
        "collected_at": persisted.collected_at.isoformat(),
        "evaluated_at": persisted.evaluated_at.isoformat(),
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/v1/evaluations/gh-001", response_model=EvaluationResponse)
def evaluate_gh001_endpoint(
    request: GH001EvaluationRequest,
    http_request: Request,
    session: Session = Depends(get_db_session),
    github_token: str = Depends(get_github_token),
    current_user: User = Depends(get_current_user)
):
    """
    Executes the GH-001 control evaluation on a GitHub repository.
    """
    _require_repository_authorization(session, current_user, request.owner, request.repository)
    repo = PostgresEvaluationRepository_Dependency_Wrapper(session)
    reservation_id = _reserve_trial_evaluation(
        session, current_user, f"{request.owner}/{request.repository}", http_request.headers.get("Idempotency-Key")
    )
    try:
        persisted = evaluate_and_store_gh001(
            owner=request.owner,
            repo=request.repository,
            branch=request.branch,
            token=github_token,
            repository=repo,
            requested_by_user_id=current_user.id
        )
        _complete_trial_evaluation(session, reservation_id, persisted.id)
    except ValueError as e:
        _release_trial_evaluation(session, reservation_id)
        raise HTTPException(status_code=422, detail="Invalid evidence acquired") from e
    except RuntimeError as e:
        _release_trial_evaluation(session, reservation_id)
        logger.error(f"Execution failed: {e}")
        raise HTTPException(status_code=502, detail="Infrastructure or upstream communication failure") from e
    except Exception as e:
        _release_trial_evaluation(session, reservation_id)
        logger.error(f"Unexpected internal error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e
        
    rule_obj = None
    if persisted.rule_id is not None and persisted.rule_version is not None:
        rule_obj = RuleResponse(id=persisted.rule_id, version=persisted.rule_version)

    evidence = persisted.reconstructed_evidence
    if not isinstance(evidence, GH001Evidence):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored GH-001 evidence is inconsistent")
        
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
            required_review_approvals=evidence.required_review_approvals,
            dismiss_stale_reviews=evidence.dismiss_stale_reviews,
            hash=evidence.canonical_hash()
        ),
        collected_at=persisted.collected_at.isoformat(),
        evaluated_at=persisted.evaluated_at.isoformat()
    )

def PostgresEvaluationRepository_Dependency_Wrapper(session: Session) -> EvaluationRepository:
    from securecode.adapters.postgres.repository import PostgresEvaluationRepository
    return PostgresEvaluationRepository(session)

from securecode.api.schemas import (
    GH002EvaluationRequest,
    GH002EvaluationResponse,
    GH002EvidenceResponse,
    GH003EvaluationRequest,
    GH003EvaluationResponse,
    GH003EvidenceResponse,
)
from securecode.application.evaluate_and_store import (
    evaluate_and_store_gh002,
    evaluate_and_store_gh003,
)


@app.post("/api/v1/evaluations/gh-002", response_model=GH002EvaluationResponse)
def evaluate_gh002_endpoint(
    request: GH002EvaluationRequest,
    http_request: Request,
    session: Session = Depends(get_db_session),
    github_token: str = Depends(get_github_token),
    current_user: User = Depends(get_current_user)
):
    """
    Executes the GH-002 control evaluation on a GitHub repository.
    """
    _require_repository_authorization(session, current_user, request.owner, request.repository)
    repo = PostgresEvaluationRepository_Dependency_Wrapper(session)
    reservation_id = _reserve_trial_evaluation(
        session, current_user, f"{request.owner}/{request.repository}", http_request.headers.get("Idempotency-Key")
    )
    try:
        persisted = evaluate_and_store_gh002(
            owner=request.owner,
            repo=request.repository,
            token=github_token,
            repository=repo,
            requested_by_user_id=current_user.id
        )
        _complete_trial_evaluation(session, reservation_id, persisted.id)
    except ValueError as e:
        _release_trial_evaluation(session, reservation_id)
        raise HTTPException(status_code=422, detail="Invalid evidence acquired") from e
    except RuntimeError as e:
        _release_trial_evaluation(session, reservation_id)
        logger.error(f"Execution failed: {e}")
        raise HTTPException(status_code=502, detail="Infrastructure or upstream communication failure") from e
    except Exception as e:
        _release_trial_evaluation(session, reservation_id)
        logger.error(f"Unexpected internal error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e
        
    rule_obj = None
    if persisted.rule_id is not None and persisted.rule_version is not None:
        rule_obj = RuleResponse(id=persisted.rule_id, version=persisted.rule_version)

    evidence = persisted.reconstructed_evidence
    if not isinstance(evidence, GH002Evidence):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored GH-002 evidence is inconsistent")
        
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
            default_branch=evidence.default_branch,
            protection_enabled=evidence.protection_enabled,
            hash=evidence.canonical_hash()
        ),
        collected_at=persisted.collected_at.isoformat(),
        evaluated_at=persisted.evaluated_at.isoformat()
    )


@app.post("/api/v1/evaluations/gh-003", response_model=GH003EvaluationResponse)
def evaluate_gh003_endpoint(
    request: GH003EvaluationRequest,
    http_request: Request,
    session: Session = Depends(get_db_session),
    github_token: str = Depends(get_github_token),
    current_user: User = Depends(get_current_user),
):
    """Verify that the selected GitHub branch requires signed commits."""
    _require_repository_authorization(session, current_user, request.owner, request.repository)
    repository = PostgresEvaluationRepository_Dependency_Wrapper(session)
    reservation_id = _reserve_trial_evaluation(
        session, current_user, f"{request.owner}/{request.repository}", http_request.headers.get("Idempotency-Key")
    )
    try:
        persisted = evaluate_and_store_gh003(
            owner=request.owner,
            repo=request.repository,
            branch=request.branch,
            token=github_token,
            repository=repository,
            requested_by_user_id=current_user.id,
        )
        _complete_trial_evaluation(session, reservation_id, persisted.id)
    except ValueError as error:
        _release_trial_evaluation(session, reservation_id)
        raise HTTPException(status_code=422, detail="Invalid evidence acquired") from error
    except RuntimeError as error:
        _release_trial_evaluation(session, reservation_id)
        logger.error("GH-003 execution failed: %s", error)
        raise HTTPException(status_code=502, detail="Infrastructure or upstream communication failure") from error
    except Exception as error:
        _release_trial_evaluation(session, reservation_id)
        logger.error("Unexpected GH-003 error: %s", error)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error

    rule = RuleResponse(id=persisted.rule_id, version=persisted.rule_version) if persisted.rule_id and persisted.rule_version else None
    evidence = persisted.reconstructed_evidence
    if not isinstance(evidence, GH003Evidence):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored GH-003 evidence is inconsistent")
    return GH003EvaluationResponse(
        evaluation_id=str(persisted.id),
        control_id=persisted.control_id,
        rule=rule,
        status=persisted.status.name,
        source=SourceResponse(type=persisted.source_type, repository=persisted.source_repository, branch=persisted.source_branch),
        evidence=GH003EvidenceResponse(
            branch=evidence.branch,
            required_signatures_enabled=evidence.required_signatures_enabled,
            hash=evidence.canonical_hash(),
        ),
        collected_at=persisted.collected_at.isoformat(),
        evaluated_at=persisted.evaluated_at.isoformat(),
    )
