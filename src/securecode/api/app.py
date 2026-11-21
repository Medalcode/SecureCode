import hashlib
import json
import logging
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, TypedDict
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
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
    OrganizationMembership,
    RepositoryAuthorization,
    ServiceDocumentAcceptance,
    SubscriptionEvent,
    User,
    UserAuditEvent,
    UserFinOpsSettings,
    UserSession,
    UserSettings,
    UserSubscription,
)
from securecode.api.dependencies import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_current_user,
    get_db_session,
    get_engine,
    get_github_token,
    require_platform_admin,
    require_same_origin,
)
from securecode.api.public_site import LEGAL_CONTENT, public_page
from securecode.api.schemas import (
    EvaluationResponse,
    EvidenceResponse,
    GH001EvaluationRequest,
    RuleResponse,
    SourceResponse,
)
from securecode.api.service_document_manifest import load_document_manifest
from securecode.api.service_documents import ACCEPTANCE_TYPE, current_onboarding_package
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
from securecode.application.evaluation_report import build_evaluation_report_pdf
from securecode.application.result_explanation import build_result_explanation
from securecode.config import validate_environment
from securecode.domain.roles import (
    ANALYST,
    ORGANIZATION_OWNER,
    PLATFORM_ADMIN,
    canonical_role,
    is_organization_owner,
    is_platform_admin,
)
from securecode.engine.evaluator import get_rules_directory
from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence
from securecode.observability import (
    REQUEST_ID_HEADER,
    ObservabilityMiddleware,
    configure_logging,
    get_metrics_snapshot,
    get_request_id,
    log_critical_error,
    log_event,
    metrics,
    readiness_status,
)
from securecode.ports.evaluation_repository import (
    EvaluationRepository,
    PersistedEvaluation,
)

configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_environment()
    yield


app = FastAPI(
    title="SecureCode API",
    description="API de evaluación de controles GitHub GH-001, GH-002 y GH-003, con administración, auditoría y FinOps.",
    version="1.0.0",
    lifespan=lifespan,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach browser protections without coupling them to the reverse proxy."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith("/api/v1/auth/"):
            response.headers["Cache-Control"] = "no-store"
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
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", REQUEST_ID_HEADER],
    )
app.add_middleware(ObservabilityMiddleware)

logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, error: Exception) -> JSONResponse:
    log_critical_error(
        "http.request.unhandled",
        error_type=type(error).__name__,
        method=request.method,
        route=getattr(request.scope.get("route"), "path", "unmatched"),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error"},
        headers={REQUEST_ID_HEADER: get_request_id()},
    )

# Montaje de archivos estaticos para la interfaz de usuario moderna
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
@app.get("/controles", response_class=HTMLResponse)
@app.get("/alcance", response_class=HTMLResponse)
@app.get("/nosotros", response_class=HTMLResponse)
@app.get("/contacto", response_class=HTMLResponse)
@app.get("/preguntas-frecuentes", response_class=HTMLResponse)
@app.get("/legal/{document}", response_class=HTMLResponse)
def serve_public_site(request: Request, document: str | None = None):
    """Serve public pages without exposing the authenticated application shell."""
    no_store_headers = {"Cache-Control": "no-store, max-age=0"}
    if document is not None and document not in LEGAL_CONTENT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    return HTMLResponse(content=public_page(request.url.path), headers=no_store_headers)


@app.get("/app", response_class=HTMLResponse)
def serve_index():
    """Serve the authenticated application shell without caching sensitive UI."""
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
def get_system_overview(_: User = Depends(require_platform_admin)):
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


@app.get("/internal/observability/metrics")
def get_observability_metrics(_: User = Depends(require_platform_admin)):
    """Aggregated, low-cardinality counters for the current process only."""
    return get_metrics_snapshot()


from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, Field

from securecode.api.security import (
    create_access_token,
    get_jwt_expire_minutes,
    hash_password,
    verify_password,
)

# Equalize the expensive password-verification path for unknown usernames.
# This reduces timing-based account enumeration without persisting a fake user.
_DUMMY_PASSWORD_HASH = hash_password("securecode-login-timing-placeholder")

class Token(BaseModel):
    access_token: str
    token_type: str


class BrowserSessionResponse(BaseModel):
    csrf_token: str
    username: str
    role: Literal["platform_admin", "organization_owner", "analyst"]


class CurrentUserResponse(BaseModel):
    username: str
    active: bool
    role: Literal["platform_admin", "organization_owner", "analyst"]


class OrganizationRegistrationRequest(BaseModel):
    # Registration is a public privilege boundary: silently ignoring a caller's
    # requested role would hide malformed or hostile requests from clients.
    model_config = ConfigDict(extra="forbid")
    organization_name: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=12, max_length=128)
    password_confirmation: str = Field(min_length=12, max_length=128)
    accepted_document_package_id: str = Field(min_length=1, max_length=64)
    accepted_document_package_version: str = Field(min_length=1, max_length=32)
    accepted_document_package_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    acceptance_confirmed: bool = False


class OrganizationRegistrationResponse(CurrentUserResponse):
    organization_id: str
    organization_name: str


class ServiceDocumentSummary(BaseModel):
    document_id: str
    version: str
    title: str
    path: str
    sha256: str


class CurrentDocumentPackageResponse(BaseModel):
    package_id: str
    version: str
    sha256: str
    documents: list[ServiceDocumentSummary]


class ServiceDocumentAcceptanceResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    package_id: str
    package_version: str
    document_id: str
    document_version: str
    document_sha256: str
    package_sha256: str
    source_path: str
    acceptance_type: str
    accepted_at: datetime


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["platform_admin"] = PLATFORM_ADMIN


class UserUpdateRequest(BaseModel):
    active: bool | None = None
    role: Literal["platform_admin"] | None = None
    password: str | None = Field(default=None, min_length=12, max_length=128)


class UserResponse(BaseModel):
    id: str
    username: str
    active: bool
    role: Literal["platform_admin", "organization_owner", "analyst"]
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


class OrganizationMemberCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str | None = Field(default=None, max_length=128,
        description="Contraseña del Analyst (mínimo 12 caracteres). Ausente, nula, vacía o de sólo espacios equivale a no proporcionada: la estrategia la define generate_temp.")
    generate_temp: bool = Field(default=False, description="Si es true, el sistema genera una contraseña temporal segura y la muestra una sola vez al Owner con aviso de copiarla y entregarla por canal seguro.")


class OrganizationMemberUpdateRequest(BaseModel):
    active: bool | None = None
    password: str | None = Field(default=None, max_length=128,
        description="Nueva contraseña del Analyst (mínimo 12 caracteres). Ausente, nula, vacía o de sólo espacios equivale a no proporcionada: la estrategia la define generate_temp.")
    generate_temp: bool = Field(default=False, description="Si es true, el sistema genera una contraseña temporal segura y la muestra una sola vez al Owner con aviso de copiarla y entregarla por canal seguro.")


class OrganizationMemberResponse(UserResponse):
    organization_id: str
    organization_name: str
    temporary_password: str | None = None


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


class OrganizationAnalystEntitlementsResponse(BaseModel):
    """The active Analyst-seat entitlement for one customer organization."""

    analyst_limit: int
    active_analysts: int
    analysts_remaining: int
    source: str


class FinOpsSettingsUpdateRequest(BaseModel):
    budget_clp: Literal[10, 50, 100, 200, 500, 1000]
    alert_threshold_pct: Literal[50, 80, 100]
    alert_enabled: bool


class FinOpsResponse(BaseModel):
    scope: Literal["account", "organization", "platform"]
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


@app.get("/api/v1/service-documents/current", response_model=CurrentDocumentPackageResponse)
def get_current_service_documents():
    """Publish the exact package version that public registration accepts."""
    return current_onboarding_package().as_dict()


_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_SUBSCRIPTION_PERIOD = timedelta(days=30)
class PlanCatalogEntry(TypedDict):
    """A commercial plan exposed by the subscription catalogue."""

    id: str
    name: str
    price_clp: int
    analyst_limit: int
    features: list[str]


_PLAN_CATALOG: dict[str, PlanCatalogEntry] = {
    "pro": {
        "id": "pro",
        "name": "Pro",
        "price_clp": 150025,
        "analyst_limit": 3,
        "features": ["3 controles canónicos", "Hasta 3 Analyst", "Evidencia SHA-256", "Historial y exportación CSV"],
    },
    "premium": {
        "id": "premium",
        "name": "Premium",
        "price_clp": 375064,
        "analyst_limit": 10,
        "features": ["Todo lo incluido en Pro", "Hasta 10 Analyst", "Soporte prioritario según contrato"],
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
    # GitHub identifica owner y repository sin distinguir mayúsculas. Canonicalizar.
    # evita que ``Acme/App`` y ``acme/app`` creen alcances distintos por accidente.
    return repository.lower()


def _require_repository_authorization(session: Session, current_user: User, owner: str, repository: str) -> None:
    """Customer users require explicit repository or trial scope."""
    if is_platform_admin(getattr(current_user, "role", None)):
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
            detail="Tu cuenta no está autorizada para evaluar este repositorio. Solicita acceso al propietario de tu organización.",
        )


def _validate_password_strength(password: str) -> None:
    if not (len(password) >= 12 and re.search(r"[a-z]", password) and re.search(r"[A-Z]", password) and re.search(r"\d", password) and re.search(r"[^A-Za-z0-9]", password)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La contraseña debe tener 12+ caracteres, mayúscula, minúscula, número y símbolo",
        )


def _normalise_requested_password(raw: str | None) -> str | None:
    """Return the explicit password, or None when it is absent/blank.

    An absent, null, empty or whitespace-only password is treated as "not
    provided", so the generate_temp flag alone decides the strategy. A
    non-blank password is trimmed so the value shown, validated and hashed
    is exactly one password.
    """
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped if stripped else None


def _generate_secure_temp_password() -> str:
    """Generate a secure temporary password for Analyst creation/reset.

    The password is generated cryptographically securely, hashed before storage,
    and returned in plaintext ONLY in the API response for the creation/reset
    call. It must NOT persist in logs, audit records, or subsequent responses.
    """
    import secrets
    import string
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*"
    # Guarantee at least one character of every class the password policy
    # requires, so generation can never randomly violate its own policy.
    chars = [
        secrets.choice(lower),
        secrets.choice(upper),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]
    alphabet = lower + upper + digits + symbols
    chars.extend(secrets.choice(alphabet) for _ in range(12))
    # Fisher-Yates shuffle driven by cryptographically secure randomness.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def _record_user_audit(session: Session, actor_id: UUID | None, target_id: UUID | None, action: str, details: dict) -> None:
    """Record account lifecycle changes without persisting credentials or tokens."""
    session.add(UserAuditEvent(
        id=uuid4(), actor_user_id=actor_id, target_user_id=target_id,
        action=action, details=details, created_at=datetime.now(UTC),
    ))


def _issue_user_session(session: Session, user: User, csrf_token: str | None = None) -> str:
    jti = str(uuid4())
    now = datetime.now(UTC)
    csrf_token_hash = hashlib.sha256(csrf_token.encode()).hexdigest() if csrf_token else None
    session.add(UserSession(
        id=uuid4(), user_id=user.id, jti=jti, created_at=now,
        expires_at=now + timedelta(minutes=get_jwt_expire_minutes()),
        last_seen_at=now, revoked_at=None, revoked_reason=None,
        csrf_token_hash=csrf_token_hash,
    ))
    return create_access_token(str(user.id), jti=jti)


def _secure_cookie(request: Request) -> bool:
    environment = os.environ.get("APP_ENV", "development").strip().lower()
    return environment in {"staging", "production"} or request.url.scheme == "https"


def _revoke_user_sessions(
    session: Session,
    user_id: UUID,
    reason: str,
    jti: str | None = None,
) -> int:
    query = session.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.revoked_at.is_(None),
    )
    if jti is not None:
        query = query.filter(UserSession.jti == jti)
    revoked_at = datetime.now(UTC)
    values: dict[Any, Any] = {UserSession.revoked_at: revoked_at, UserSession.revoked_reason: reason}
    if hasattr(query, "update"):
        return int(query.update(values, synchronize_session=False))
    rows = query.all()
    for row in rows:
        row.revoked_at = revoked_at
        row.revoked_reason = reason
    return len(rows)


def _membership_for_user(session: Session, user_id: UUID) -> OrganizationMembership | None:
    """Return the single customer tenancy supported by the current MVP."""
    query = (
        session.query(OrganizationMembership)
        .filter(OrganizationMembership.user_id == user_id)
        .order_by(OrganizationMembership.created_at.asc())
    )
    try:
        memberships = list(query.all())
    except AttributeError:
        memberships = []
    if memberships and not hasattr(memberships[0], "role"):
        first = query.first()
        memberships = [first] if first is not None else []
    if len(memberships) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Multiple organization memberships are not supported",
        )
    if memberships:
        return memberships[0]
    first = query.first()
    return first if isinstance(first, OrganizationMembership) or hasattr(first, "role") else None


def _require_organization_owner(session: Session, current_user: User) -> OrganizationMembership:
    """Resolve an active customer's owner membership without trusting the UI."""
    if not is_organization_owner(getattr(current_user, "role", None)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization owner role required")
    membership = _membership_for_user(session, current_user.id)
    if membership is None or membership.role != ORGANIZATION_OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization owner membership required")
    return membership


def _organization_response(session: Session, membership: OrganizationMembership) -> tuple[OrganizationMembership, Organization]:
    organization = session.query(Organization).filter(Organization.id == membership.organization_id).first()
    if organization is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization membership is inconsistent")
    return membership, organization


def _organization_member_response(user: User, organization: Organization) -> dict:
    return {
        **_user_response(user),
        "organization_id": str(organization.id),
        "organization_name": organization.name,
    }


def _can_access_organization_user(session: Session, current_user: User, target_user_id: UUID | None) -> bool:
    """Apply the customer boundary to history and evidence reads."""
    if is_platform_admin(getattr(current_user, "role", None)):
        return True
    if target_user_id is None:
        return False
    if current_user.id == target_user_id:
        return True
    if not is_organization_owner(getattr(current_user, "role", None)):
        return False
    membership = _membership_for_user(session, current_user.id)
    if membership is None:
        return False
    return session.query(OrganizationMembership).filter(
        OrganizationMembership.organization_id == membership.organization_id,
        OrganizationMembership.user_id == target_user_id,
    ).first() is not None


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
    session.flush()
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


def _organization_analyst_entitlement(
    session: Session,
    *,
    owner: User,
    organization: Organization,
) -> tuple[int, int, str]:
    """Resolve active Analyst seats from the owner's plan or active trial.

    A technical Enterprise Trial deliberately permits one Analyst only. Normal
    subscriptions use the catalogued seat count. Enterprise contractual seats
    must be modelled as an organization entitlement before that plan is sold;
    they are not inferred or treated as unlimited here.
    """
    trial = get_active_trial_for_user(session, owner.id)
    if trial is not None and trial.organization_id == organization.id:
        limit, source = 1, "Enterprise Trial"
    else:
        subscription = _ensure_subscription(session, owner.id)
        plan = _PLAN_CATALOG.get(subscription.plan_id, _PLAN_CATALOG["pro"])
        limit, source = int(plan["analyst_limit"]), str(plan["name"])

    active = (
        session.query(func.count(OrganizationMembership.id))
        .join(User, User.id == OrganizationMembership.user_id)
        .filter(
            OrganizationMembership.organization_id == organization.id,
            OrganizationMembership.role == ANALYST,
            User.active.is_(True),
        )
        .scalar()
        or 0
    )
    return limit, int(active), source


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
    if is_platform_admin(getattr(current_user, "role", None)):
        scope = "platform"
    elif is_organization_owner(getattr(current_user, "role", None)):
        membership = _membership_for_user(session, current_user.id)
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization membership required")
        member_ids = [member_id for (member_id,) in session.query(OrganizationMembership.user_id).filter(
            OrganizationMembership.organization_id == membership.organization_id
        ).all()]
        query = query.filter(EvaluationRecord.requested_by_user_id.in_(member_ids))
        scope = "organization"
    else:
        scope = "account"
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


@app.get("/api/v1/management-report")
def management_report(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return a factual, organization-scoped management report.

    This endpoint deliberately reports persisted SecureCode activity only. It
    never fabricates billing, availability, or operational metrics that have
    not been integrated with their source systems.
    """
    membership = _require_organization_owner(session, current_user)
    organization = session.query(Organization).filter(Organization.id == membership.organization_id).first()
    if organization is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization membership required")

    members = (
        session.query(OrganizationMembership, User)
        .join(User, User.id == OrganizationMembership.user_id)
        .filter(OrganizationMembership.organization_id == organization.id)
        .all()
    )
    member_ids = [member.user_id for member, _ in members]
    usernames = {user.id: user.username for _, user in members}
    records = (
        session.query(EvaluationRecord)
        .filter(EvaluationRecord.requested_by_user_id.in_(member_ids))
        .order_by(EvaluationRecord.evaluated_at.desc())
        .all()
    ) if member_ids else []

    period_start = _period_start_utc()
    statuses = {"PASS": 0, "FAIL": 0, "UNKNOWN": 0}
    controls: dict[str, dict[str, int]] = {}
    repositories: dict[str, dict[str, int]] = {}
    current_period = 0
    for record in records:
        normalized_status = record.status.upper()
        if normalized_status not in statuses:
            normalized_status = "UNKNOWN"
        statuses[normalized_status] += 1
        evaluated_at = record.evaluated_at
        # SQLite used by the isolated HTTP tests may return a naive datetime;
        # production PostgreSQL stores the same value as UTC-aware.
        if evaluated_at.tzinfo is None:
            evaluated_at = evaluated_at.replace(tzinfo=UTC)
        if evaluated_at >= period_start:
            current_period += 1
        for bucket, key in ((controls, record.control_id), (repositories, record.source_repository)):
            metrics = bucket.setdefault(key, {"total": 0, "pass": 0, "fail": 0, "unknown": 0})
            metrics["total"] += 1
            metrics[normalized_status.lower()] += 1

    active_analysts = sum(1 for member, user in members if member.role == ANALYST and user.active)
    authorization_rows = (
        session.query(RepositoryAuthorization)
        .filter(
            RepositoryAuthorization.user_id.in_(member_ids),
            RepositoryAuthorization.active.is_(True),
        )
        .all()
    ) if member_ids else []
    subscription = _ensure_subscription(session, current_user.id)
    plan = _PLAN_CATALOG.get(subscription.plan_id, _PLAN_CATALOG["pro"])
    finops = _ensure_finops_settings(session, current_user.id)
    decisive = statuses["PASS"] + statuses["FAIL"]

    def breakdown(source: dict[str, dict[str, int]], label: str) -> list[dict]:
        return [
            {label: name, **metrics}
            for name, metrics in sorted(source.items(), key=lambda item: (-item[1]["total"], item[0]))
        ]

    return {
        "generated_at": datetime.now(UTC),
        "scope": "organization",
        "organization": {"name": organization.name},
        "period": {"start": period_start, "label": "Mes calendario actual (UTC)"},
        "summary": {
            "evaluations_all_time": len(records),
            "evaluations_current_period": current_period,
            "pass_count": statuses["PASS"],
            "fail_count": statuses["FAIL"],
            "unknown_count": statuses["UNKNOWN"],
            "conformance_rate_pct": round((statuses["PASS"] / decisive) * 100, 1) if decisive else None,
            "active_analysts": active_analysts,
            "active_repository_authorizations": len(authorization_rows),
            "unique_authorized_repositories": len({item.repository for item in authorization_rows}),
        },
        "subscription": {
            "plan_id": subscription.plan_id,
            "plan_name": plan["name"],
            "expires_at": subscription.expires_at,
            "billing_mode": "demo_non_billable",
        },
        "finops_preferences": {
            "budget_clp": finops.budget_clp,
            "alert_threshold_pct": finops.alert_threshold_pct,
            "alert_enabled": finops.alert_enabled,
            "billing_data_state": "not_connected",
        },
        "by_control": breakdown(controls, "control_id"),
        "by_repository": breakdown(repositories, "repository"),
        "recent_evaluations": [
            {
                "control_id": record.control_id,
                "status": record.status.upper(),
                "repository": record.source_repository,
                "branch": record.source_branch,
                "evaluated_at": record.evaluated_at,
                "requested_by": usernames.get(record.requested_by_user_id, "Cuenta no disponible"),
            }
            for record in records[:10]
        ],
        "data_sources": {
            "evaluations": "Base de datos de SecureCode",
            "subscription": "Configuración de suscripción de demostración",
            "billing": "not_connected",
        },
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

def _authenticate_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm,
    session: Session,
) -> User:
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
    if not user or not password_valid or not user.active:
        _record_failed_login(session, scope_hash, now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user.last_login_at = datetime.now(UTC)
    _clear_failed_logins(session, scope_hash)
    return user


def _commit_login_session(session: Session) -> None:
    try:
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Could not create authenticated session")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo iniciar la sesión",
        ) from None


@app.post("/api/v1/auth/token", response_model=Token)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_db_session),
):
    user = _authenticate_login(request, form_data, session)
    access_token = _issue_user_session(session, user)
    _commit_login_session(session)
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/v1/auth/session", response_model=BrowserSessionResponse)
def login_browser_session(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_db_session),
):
    require_same_origin(request)
    user = _authenticate_login(request, form_data, session)
    csrf_token = secrets.token_urlsafe(32)
    access_token = _issue_user_session(session, user, csrf_token=csrf_token)
    _commit_login_session(session)
    max_age = get_jwt_expire_minutes() * 60
    secure = _secure_cookie(request)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        access_token,
        max_age=max_age,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=max_age,
        path="/",
        secure=secure,
        httponly=False,
        samesite="lax",
    )
    return {
        "csrf_token": csrf_token,
        "username": user.username,
        "role": canonical_role(user.role),
    }


@app.post("/api/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
):
    _revoke_user_sessions(session, principal.user.id, "logout", jti=principal.jti)
    session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    if principal.mode == "cookie":
        secure = _secure_cookie(request)
        response.delete_cookie(SESSION_COOKIE_NAME, path="/", secure=secure, samesite="lax")
        response.delete_cookie(CSRF_COOKIE_NAME, path="/", secure=secure, samesite="lax")
    return response


@app.post("/api/v1/auth/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
):
    _revoke_user_sessions(session, principal.user.id, "logout_all")
    session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    if principal.mode == "cookie":
        secure = _secure_cookie(request)
        response.delete_cookie(SESSION_COOKIE_NAME, path="/", secure=secure, samesite="lax")
        response.delete_cookie(CSRF_COOKIE_NAME, path="/", secure=secure, samesite="lax")
    return response


@app.post("/api/v1/auth/register", response_model=OrganizationRegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_organization_owner(
    request: OrganizationRegistrationRequest,
    session: Session = Depends(get_db_session),
):
    """Create the first customer identity after explicit document acceptance.

    Public registration is intentionally limited to the organization owner role.
    Platform administration can never be requested through this boundary.
    """
    if request.password != request.password_confirmation:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Las contraseñas no coinciden")
    package = current_onboarding_package()
    manifest = load_document_manifest()
    if not request.acceptance_confirmed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Debe aceptar las condiciones del servicio y el alcance técnico")
    if request.accepted_document_package_id != package.package_id or request.accepted_document_package_version != package.version:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="La versión de los documentos aceptados no es vigente")
    if request.accepted_document_package_sha256 != package.sha256:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="La huella de los documentos aceptados no es vigente")
    username = _normalise_username(request.username)
    organization_name = request.organization_name.strip()
    if len(organization_name) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="El nombre de la organización debe tener al menos 2 caracteres")
    _validate_password_strength(request.password)
    if session.query(User).filter(User.username == username).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    if session.query(Organization).filter(func.lower(Organization.name) == organization_name.lower()).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization name already exists")

    now = datetime.now(UTC)
    owner = User(
        id=uuid4(), username=username, password_hash=hash_password(request.password), active=True,
        role=ORGANIZATION_OWNER, created_at=now, updated_at=now,
    )
    organization = Organization(id=uuid4(), name=organization_name, created_at=now)
    membership = OrganizationMembership(
        id=uuid4(), organization_id=organization.id, user_id=owner.id,
        role=ORGANIZATION_OWNER, created_at=now,
    )
    acceptances = [
        ServiceDocumentAcceptance(
            id=uuid4(),
            organization_id=organization.id,
            user_id=owner.id,
            package_id=package.package_id,
            package_version=package.version,
            document_id=document.document_id,
            document_version=document.version,
            document_sha256=document.sha256,
            package_sha256=package.sha256,
            source_path=document.path,
            acceptance_type=ACCEPTANCE_TYPE,
            accepted_at=now,
        )
        for document in package.documents
    ]
    try:
        # Persist the foreign-key targets first. PostgreSQL enforces these
        # constraints immediately, while SQLite test configurations may not.
        session.add_all((owner, organization))
        session.flush()
        session.add_all((membership, *acceptances))
        _record_user_audit(session, owner.id, owner.id, "organization_registered", {
            "organization_id": str(organization.id), "organization_name": organization.name,
            "role": ORGANIZATION_OWNER,
            "accepted_document_package": package.package_id,
            "accepted_document_package_version": package.version,
            "accepted_document_package_sha256": package.sha256,
            "accepted_document_manifest_version": manifest["manifest_version"],
            "accepted_document_ids": [document.document_id for document in package.documents],
            "acceptance_type": ACCEPTANCE_TYPE,
        })
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        # Do not disclose persistence failures to the public registration
        # response. Record only safe diagnostics for operators: exception type
        # and an optional PostgreSQL constraint identifier, never SQL values.
        diagnostics = getattr(getattr(error, "orig", None), "diag", None)
        constraint_name = getattr(diagnostics, "constraint_name", None)
        if constraint_name:
            logger.error(
                "Organization registration persistence failed (type=%s, constraint=%s)",
                type(error).__name__,
                constraint_name,
            )
        else:
            logger.error(
                "Organization registration persistence failed (type=%s)",
                type(error).__name__,
            )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se pudo crear la organización") from error
    return {
        "username": owner.username, "active": owner.active, "role": owner.role,
        "organization_id": str(organization.id), "organization_name": organization.name,
    }


@app.get("/api/v1/organization/service-acceptances", response_model=list[ServiceDocumentAcceptanceResponse])
def list_service_document_acceptances(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    membership = _require_organization_owner(session, current_user)
    records = (
        session.query(ServiceDocumentAcceptance)
        .filter(ServiceDocumentAcceptance.organization_id == membership.organization_id)
        .order_by(ServiceDocumentAcceptance.accepted_at.desc(), ServiceDocumentAcceptance.id.desc())
        .all()
    )
    return [
        {
            "id": str(record.id),
            "organization_id": str(record.organization_id),
            "user_id": str(record.user_id),
            "package_id": record.package_id,
            "package_version": record.package_version,
            "document_id": record.document_id,
            "document_version": record.document_version,
            "document_sha256": record.document_sha256,
            "package_sha256": record.package_sha256,
            "source_path": record.source_path,
            "acceptance_type": record.acceptance_type,
            "accepted_at": record.accepted_at,
        }
        for record in records
    ]


@app.get("/api/v1/organization/members", response_model=list[OrganizationMemberResponse])
def list_organization_members(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    membership = _require_organization_owner(session, current_user)
    _, organization = _organization_response(session, membership)
    users = (
        session.query(User)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .filter(OrganizationMembership.organization_id == organization.id)
        .order_by(User.username.asc())
        .all()
    )
    return [_organization_member_response(user, organization) for user in users]


@app.get("/api/v1/organization/analyst-entitlements", response_model=OrganizationAnalystEntitlementsResponse)
def get_organization_analyst_entitlements(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Show the Owner the seat limit that is enforced on Analyst creation."""
    membership = _require_organization_owner(session, current_user)
    _, organization = _organization_response(session, membership)
    limit, active, source = _organization_analyst_entitlement(
        session, owner=current_user, organization=organization,
    )
    return {
        "analyst_limit": limit,
        "active_analysts": active,
        "analysts_remaining": max(0, limit - active),
        "source": source,
    }


@app.post("/api/v1/organization/members", response_model=OrganizationMemberResponse, status_code=status.HTTP_201_CREATED)
def create_organization_member(
    request: OrganizationMemberCreateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Let a customer owner provision an analyst without platform privileges."""
    membership = _require_organization_owner(session, current_user)
    _, organization = _organization_response(session, membership)
    # Lock the organization while counting seats. This prevents two concurrent
    # requests from both observing the final available Analyst seat.
    organization = session.query(Organization).filter(Organization.id == organization.id).with_for_update().one()
    username = _normalise_username(request.username)

    # --- Password resolution path ---
    # XOR: exactamente una alternativa debe ser válida. Una contraseña
    # ausente, nula, vacía o de sólo espacios equivale a "no proporcionada".
    explicit_password = _normalise_requested_password(request.password)
    generate_temp_requested = request.generate_temp

    # Contraseña útil y generate_temp a la vez: rechazar 422
    if explicit_password is not None and generate_temp_requested:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalido: proporcione una alternativa: contraseña explícita O generate_temp=true, no los dos.",
        )
    # Sólo contraseña explícita (sin generate_temp)
    if explicit_password is not None:
        _validate_password_strength(explicit_password)
        password_to_use: str = explicit_password
        temp_password = None
        generate_temp_flag = False
    # Sólo generate_temp (sin contraseña útil)
    elif generate_temp_requested:
        password_to_use = _generate_secure_temp_password()
        _validate_password_strength(password_to_use)
        temp_password = password_to_use  # Show once in response
        generate_temp_flag = True
    # Ninguna alternativa
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Se requiere una contraseña o definir generate_temp=true para una temporal.",
        )

    if session.query(User).filter(User.username == username).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    limit, active, source = _organization_analyst_entitlement(
        session, owner=current_user, organization=organization,
    )
    if active >= limit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Límite de Analyst alcanzado para el plan {source} ({active}/{limit}). Desactiva un Analyst o cambia de plan.",
        )
    now = datetime.now(UTC)
    analyst = User(
        id=uuid4(), username=username, password_hash=hash_password(password_to_use),  # type: ignore[arg-type]
        active=True,
        role=ANALYST, created_at=now, updated_at=now,
    )
    analyst_membership = OrganizationMembership(
        id=uuid4(), organization_id=organization.id, user_id=analyst.id,
        role=ANALYST, created_at=now,
    )
    # As with public registration, persist the analyst before the membership
    # row so PostgreSQL can satisfy organization_memberships.user_id_fkey.
    session.add(analyst)
    session.flush()
    session.add(analyst_membership)
    _record_user_audit(session, current_user.id, analyst.id, "organization_analyst_created", {
        "organization_id": str(organization.id), "role": ANALYST,
    })
    session.commit()
    response = _organization_member_response(analyst, organization)
    if generate_temp_flag and temp_password is not None:
        response["temporary_password"] = temp_password
    return response


@app.patch("/api/v1/organization/members/{user_id}", response_model=OrganizationMemberResponse)
def update_organization_member(
    user_id: UUID,
    request: OrganizationMemberUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    membership = _require_organization_owner(session, current_user)
    _, organization = _organization_response(session, membership)
    target_membership = session.query(OrganizationMembership).filter(
        OrganizationMembership.organization_id == organization.id,
        OrganizationMembership.user_id == user_id,
        OrganizationMembership.role == ANALYST,
    ).first()
    target = session.query(User).filter(User.id == user_id).first()
    if target_membership is None or target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst not found in this organization")
    changes: dict[str, object] = {}
    # --- Password resolution path for reset ---
    # XOR: exactamente una de password o generate_temp (si active no cambia).
    # Una contraseña ausente, nula, vacía o de sólo espacios equivale a "no
    # proporcionada"; sin contraseña útil ni generate_temp sólo se permite
    # cambiar active.
    explicit_password = _normalise_requested_password(request.password)
    generate_temp_requested = request.generate_temp

    if explicit_password is not None and generate_temp_requested:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalido: proporcione una alternativa: contraseña explícita O generate_temp=true, no los dos.",
        )
    elif explicit_password is not None:
        _validate_password_strength(explicit_password)
        target.password_hash = hash_password(explicit_password)
        changes["password_reset"] = True
    elif generate_temp_requested:
        # Only generate_temp provided: generate secure temp password (ONE ONLY)
        new_password = _generate_secure_temp_password()
        _validate_password_strength(new_password)
        target.password_hash = hash_password(new_password)
        changes["password_reset"] = True
        # Guardar la contraseña temporal para devolverla en la respuesta
        _temp_password_store = new_password
    # If neither password nor generate_temp: only active change is allowed below

    # --- Active state change ---
    if request.active is not None and target.active != request.active:
        changes["active"] = {"from": target.active, "to": request.active}
        target.active = request.active
    # If password/generate_temp was also processed, changes includes password_reset
    # If only active was changed, changes only contains "active"

    # --- Rejection: completely empty request (no active, no password, no generate_temp) ---
    if not changes and request.active is None and explicit_password is None and not generate_temp_requested:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No se recibió ningún cambio para aplicar. Proporcione active, una contraseña o generate_temp=true.",
        )
    target.updated_at = datetime.now(UTC)
    if changes.get("password_reset") or request.active is False:
        _revoke_user_sessions(session, target.id, "credential_or_access_change")
    audit_changes = changes.copy()
    # Eliminar la contraseña del audit log por seguridad.
    if "_temp_password_store" in locals():
        audit_changes.pop("_temp_password_store", None)
    _record_user_audit(session, current_user.id, target.id, "organization_analyst_updated", audit_changes)
    session.commit()
    response = _organization_member_response(target, organization)
    # Devolver la misma contraseña temporal que se guardó, nunca una nueva.
    if "_temp_password_store" in locals():
        response["temporary_password"] = _temp_password_store
    else:
        # No se generó contraseña temporal; si el cliente pide generate_temp pero no había estado previo,
        # se responde 500 controlado sin generar una nueva ni revelar datos sensibles.
        if generate_temp_requested:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno: no fue posible almacenar la contraseña temporal generada.",
            )
    return response


@app.get("/api/v1/auth/me", response_model=CurrentUserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Return the authenticated identity; never expose password material."""
    return {
        "username": current_user.username,
        "active": current_user.active,
        "role": canonical_role(getattr(current_user, "role", ANALYST)),
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
    """Return the current organization's 30-day demo subscription."""
    _require_organization_owner(session, current_user)
    return _subscription_response(_ensure_subscription(session, current_user.id))


@app.patch("/api/v1/subscription", response_model=SubscriptionResponse)
def change_subscription(
    request: SubscriptionChangeRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Confirm one subscription change per 30-day period; this endpoint never bills."""
    _require_organization_owner(session, current_user)
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
    """List the organization owner's confirmed subscription lifecycle events."""
    _require_organization_owner(session, current_user)
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
    """Return measurable organization consumption and non-billable preferences."""
    _require_organization_owner(session, current_user)
    settings = _ensure_finops_settings(session, current_user.id)
    return _finops_response(session, current_user, settings)


@app.patch("/api/v1/finops", response_model=FinOpsResponse)
def update_finops(
    request: FinOpsSettingsUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Persist organization alert preferences; never imply Cloud Billing connectivity."""
    _require_organization_owner(session, current_user)
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
    if getattr(current_user, "role", None) not in {ORGANIZATION_OWNER, ANALYST}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer role required")
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
    membership = _require_organization_owner(session, current_user)
    if not request.confirmation:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Debes confirmar la activación del trial")
    if get_trial_for_user(session, current_user.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta cuenta ya utilizó su Enterprise Trial")
    try:
        trial = create_trial(
            session,
            owner_user_id=current_user.id,
            organization_id=membership.organization_id,
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
        "role": canonical_role(getattr(user, "role", ANALYST)),
        "created_at": user.created_at,
        "updated_at": getattr(user, "updated_at", user.created_at),
        "last_login_at": getattr(user, "last_login_at", None),
    }


@app.get("/api/v1/admin/users", response_model=list[UserResponse])
def list_users(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_platform_admin),
):
    return [_user_response(user) for user in session.query(User).order_by(User.username).all()]


@app.post("/api/v1/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: UserCreateRequest,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_platform_admin),
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
    current_admin: User = Depends(require_platform_admin),
):
    user = session.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if str(user.id) == str(current_admin.id) and request.active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrators cannot remove their own access")
    removes_admin_access = user.role == PLATFORM_ADMIN and user.active and request.active is False
    if removes_admin_access:
        active_admins = session.query(User).filter(User.role == PLATFORM_ADMIN, User.active.is_(True)).count()
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
    _revoke_user_sessions(session, user.id, "credential_or_access_change")
    _record_user_audit(session, current_admin.id, user.id, "account_updated", changes)
    session.commit()
    session.refresh(user)
    return _user_response(user)


@app.get("/api/v1/admin/user-audit-events", response_model=list[UserAuditEventResponse])
def list_user_audit_events(
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_db_session),
    _: User = Depends(require_platform_admin),
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
    _: User = Depends(require_platform_admin),
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
    current_admin: User = Depends(require_platform_admin),
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
    current_admin: User = Depends(require_platform_admin),
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


def _organization_analyst(session: Session, organization_id: UUID, user_id: UUID) -> User:
    membership = session.query(OrganizationMembership).filter(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_id == user_id,
        OrganizationMembership.role == ANALYST,
    ).first()
    user = session.query(User).filter(User.id == user_id, User.role == ANALYST).first()
    if membership is None or user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst not found in this organization")
    return user


@app.get("/api/v1/organization/repository-authorizations", response_model=list[RepositoryAuthorizationResponse])
def list_organization_repository_authorizations(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    membership = _require_organization_owner(session, current_user)
    member_ids = [member_id for (member_id,) in session.query(OrganizationMembership.user_id).filter(
        OrganizationMembership.organization_id == membership.organization_id,
        OrganizationMembership.role == ANALYST,
    ).all()]
    authorizations = session.query(RepositoryAuthorization).filter(
        RepositoryAuthorization.user_id.in_(member_ids)
    ).order_by(RepositoryAuthorization.repository.asc()).all() if member_ids else []
    users = session.query(User).filter(User.id.in_(member_ids)).all() if member_ids else []
    usernames = {user.id: user.username for user in users}
    return [_repository_authorization_response(item, usernames.get(item.user_id)) for item in authorizations]


@app.post("/api/v1/organization/repository-authorizations", response_model=RepositoryAuthorizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization_repository_authorization(
    request: RepositoryAuthorizationRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    membership = _require_organization_owner(session, current_user)
    target_user = _organization_analyst(session, membership.organization_id, request.user_id)
    repository = _normalise_repository(request.repository)
    authorization = session.query(RepositoryAuthorization).filter(
        RepositoryAuthorization.user_id == target_user.id,
        func.lower(RepositoryAuthorization.repository) == repository,
    ).first()
    if authorization is not None and authorization.active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El repositorio ya está autorizado para esta cuenta")
    if authorization is None:
        authorization = RepositoryAuthorization(
            id=uuid4(), user_id=target_user.id, repository=repository, active=True,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        session.add(authorization)
        action = "organization_repository_authorization_created"
    else:
        authorization.active = True
        authorization.updated_at = datetime.now(UTC)
        action = "organization_repository_authorization_reactivated"
    _record_user_audit(session, current_user.id, target_user.id, action, {
        "organization_id": str(membership.organization_id), "repository": repository,
    })
    session.commit()
    return _repository_authorization_response(authorization, target_user.username)


@app.patch("/api/v1/organization/repository-authorizations/{authorization_id}", response_model=RepositoryAuthorizationResponse)
def update_organization_repository_authorization(
    authorization_id: UUID,
    request: RepositoryAuthorizationUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    membership = _require_organization_owner(session, current_user)
    authorization = session.query(RepositoryAuthorization).filter(RepositoryAuthorization.id == authorization_id).first()
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository authorization not found")
    target_user = _organization_analyst(session, membership.organization_id, authorization.user_id)
    if authorization.active == request.active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="No se recibió ningún cambio para aplicar")
    authorization.active = request.active
    authorization.updated_at = datetime.now(UTC)
    _record_user_audit(session, current_user.id, target_user.id, "organization_repository_authorization_updated", {
        "organization_id": str(membership.organization_id), "repository": authorization.repository,
        "active": request.active,
    })
    session.commit()
    return _repository_authorization_response(authorization, target_user.username)


@app.get("/api/v1/evaluations/history")
def evaluation_history(
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return immutable evaluation metadata within the caller's authorized scope."""
    query = session.query(EvaluationRecord)
    if is_organization_owner(getattr(current_user, "role", None)):
        membership = _require_organization_owner(session, current_user)
        member_ids = [member_id for (member_id,) in session.query(OrganizationMembership.user_id).filter(
            OrganizationMembership.organization_id == membership.organization_id
        ).all()]
        query = query.filter(EvaluationRecord.requested_by_user_id.in_(member_ids))
    elif not is_platform_admin(getattr(current_user, "role", None)):
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


def _accessible_evaluation_record(
    session: Session, current_user: User, evaluation_id: UUID
) -> tuple[EvaluationRecord, PersistedEvaluation]:
    record = session.query(EvaluationRecord).filter(EvaluationRecord.id == evaluation_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    if not _can_access_organization_user(session, current_user, record.requested_by_user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    persisted = PostgresEvaluationRepository_Dependency_Wrapper(session).get_evaluation(evaluation_id)
    if not persisted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    return record, persisted


def _evaluation_evidence_fields(persisted: PersistedEvaluation) -> dict[str, object]:
    reconstructed = persisted.reconstructed_evidence
    if persisted.control_id == "GH-001" and isinstance(reconstructed, GH001Evidence):
        return {
            "required_review_approvals": reconstructed.required_review_approvals,
            "dismiss_stale_reviews": reconstructed.dismiss_stale_reviews,
        }
    if persisted.control_id == "GH-002" and isinstance(reconstructed, GH002Evidence):
        return {
            "default_branch": reconstructed.default_branch,
            "protection_enabled": reconstructed.protection_enabled,
        }
    if persisted.control_id == "GH-003" and isinstance(reconstructed, GH003Evidence):
        return {
            "branch": reconstructed.branch,
            "required_signatures_enabled": reconstructed.required_signatures_enabled,
        }
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored evaluation evidence is inconsistent")


def _stored_evidence_hash(record: EvaluationRecord, persisted: PersistedEvaluation) -> str:
    stored_hash = getattr(getattr(record, "evidence", None), "evidence_hash", None)
    if isinstance(stored_hash, str):
        return stored_hash
    return ""


def _result_explanation(persisted: PersistedEvaluation, stored_hash: str) -> dict[str, object]:
    return build_result_explanation(
        control_id=persisted.control_id,
        rule_id=persisted.rule_id,
        rule_version=persisted.rule_version,
        status=persisted.status,
        evidence=persisted.reconstructed_evidence,
        evidence_hash=stored_hash,
    )


@app.get("/api/v1/evaluations/{evaluation_id}")
def evaluation_detail(
    evaluation_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return the immutable evidence for one evaluation, subject to ownership."""
    record, persisted = _accessible_evaluation_record(session, current_user, evaluation_id)
    evidence = _evaluation_evidence_fields(persisted)
    stored_hash = _stored_evidence_hash(record, persisted)
    evidence["hash"] = persisted.reconstructed_evidence.canonical_hash()
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
        "explanation": _result_explanation(persisted, stored_hash),
    }


@app.get("/api/v1/evaluations/{evaluation_id}/report.pdf")
def evaluation_report_pdf(
    evaluation_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return a protected PDF generated only from persisted evaluation data."""
    record, persisted = _accessible_evaluation_record(session, current_user, evaluation_id)
    stored_hash = _stored_evidence_hash(record, persisted)
    generated_at = datetime.now(UTC)
    pdf_bytes = build_evaluation_report_pdf(
        evaluation_id=str(persisted.id),
        control_id=persisted.control_id,
        status=persisted.status.name,
        source_repository=persisted.source_repository,
        source_branch=persisted.source_branch,
        collected_at=persisted.collected_at.isoformat(),
        evaluated_at=persisted.evaluated_at.isoformat(),
        explanation=_result_explanation(persisted, stored_hash),
        generated_at=generated_at,
    )
    filename = f"securecode-{persisted.control_id.lower()}-{evaluation_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, max-age=0",
            "X-Content-Type-Options": "nosniff",
        },
    )


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


@app.get("/health/live")
def health_live():
    return {"status": "alive", "service": "securecode"}


@app.get("/health/ready")
def health_ready():
    ready, reason = readiness_status(get_engine)
    status_code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    payload = {"status": "ready" if ready else "not_ready", "reason": reason}
    log_event(
        logging.INFO if ready else logging.ERROR,
        "health.readiness.checked",
        reason=reason,
    )
    return JSONResponse(status_code=status_code, content=payload)


def _evaluation_status(persisted: PersistedEvaluation) -> str:
    status_value = getattr(persisted, "status", None)
    name = getattr(status_value, "name", None)
    if isinstance(name, str):
        return name
    return str(status_value).upper() if status_value is not None else "UNKNOWN"


def _record_evaluation_success(control_id: str, persisted: PersistedEvaluation, started: float) -> None:
    duration_ms = (time.perf_counter() - started) * 1000
    result_status = _evaluation_status(persisted)
    metrics.record_evaluation(control_id, result_status, "RESULT", duration_ms)
    log_event(
        logging.INFO,
        "evaluation.completed",
        control_id=control_id,
        result_status=result_status,
        outcome="RESULT",
        duration_ms=duration_ms,
    )


def _record_evaluation_error(control_id: str, error: Exception, started: float) -> None:
    duration_ms = (time.perf_counter() - started) * 1000
    metrics.record_evaluation(control_id, "NONE", "TECHNICAL_ERROR", duration_ms)
    log_critical_error(
        "evaluation.technical_error",
        error_type=type(error).__name__,
        control_id=control_id,
        result_status="NONE",
        outcome="TECHNICAL_ERROR",
        duration_ms=duration_ms,
    )


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
    started = time.perf_counter()
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
        _record_evaluation_success("GH-001", persisted, started)
    except ValueError as e:
        _release_trial_evaluation(session, reservation_id)
        _record_evaluation_error("GH-001", e, started)
        raise HTTPException(status_code=422, detail="Invalid evidence acquired") from e
    except RuntimeError as e:
        _release_trial_evaluation(session, reservation_id)
        _record_evaluation_error("GH-001", e, started)
        raise HTTPException(status_code=502, detail="Infrastructure or upstream communication failure") from e
    except Exception as e:
        _release_trial_evaluation(session, reservation_id)
        _record_evaluation_error("GH-001", e, started)
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    rule_obj = None
    if persisted.rule_id is not None and persisted.rule_version is not None:
        rule_obj = RuleResponse(id=persisted.rule_id, version=persisted.rule_version)

    evidence = persisted.reconstructed_evidence
    if not isinstance(evidence, GH001Evidence):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored GH-001 evidence is inconsistent")
    evidence_hash = evidence.canonical_hash()
    explanation = build_result_explanation(
        control_id=persisted.control_id,
        rule_id=persisted.rule_id,
        rule_version=persisted.rule_version,
        status=persisted.status,
        evidence=evidence,
        evidence_hash=evidence_hash,
    )

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
            hash=evidence_hash
        ),
        collected_at=persisted.collected_at.isoformat(),
        evaluated_at=persisted.evaluated_at.isoformat(),
        explanation=explanation
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
    started = time.perf_counter()
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
        _record_evaluation_success("GH-002", persisted, started)
    except ValueError as e:
        _release_trial_evaluation(session, reservation_id)
        _record_evaluation_error("GH-002", e, started)
        raise HTTPException(status_code=422, detail="Invalid evidence acquired") from e
    except RuntimeError as e:
        _release_trial_evaluation(session, reservation_id)
        _record_evaluation_error("GH-002", e, started)
        raise HTTPException(status_code=502, detail="Infrastructure or upstream communication failure") from e
    except Exception as e:
        _release_trial_evaluation(session, reservation_id)
        _record_evaluation_error("GH-002", e, started)
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    rule_obj = None
    if persisted.rule_id is not None and persisted.rule_version is not None:
        rule_obj = RuleResponse(id=persisted.rule_id, version=persisted.rule_version)

    evidence = persisted.reconstructed_evidence
    if not isinstance(evidence, GH002Evidence):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored GH-002 evidence is inconsistent")
    evidence_hash = evidence.canonical_hash()
    explanation = build_result_explanation(
        control_id=persisted.control_id,
        rule_id=persisted.rule_id,
        rule_version=persisted.rule_version,
        status=persisted.status,
        evidence=evidence,
        evidence_hash=evidence_hash,
    )

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
            hash=evidence_hash
        ),
        collected_at=persisted.collected_at.isoformat(),
        evaluated_at=persisted.evaluated_at.isoformat(),
        explanation=explanation
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
    started = time.perf_counter()
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
        _record_evaluation_success("GH-003", persisted, started)
    except ValueError as error:
        _release_trial_evaluation(session, reservation_id)
        _record_evaluation_error("GH-003", error, started)
        raise HTTPException(status_code=422, detail="Invalid evidence acquired") from error
    except RuntimeError as error:
        _release_trial_evaluation(session, reservation_id)
        _record_evaluation_error("GH-003", error, started)
        raise HTTPException(status_code=502, detail="Infrastructure or upstream communication failure") from error
    except Exception as error:
        _release_trial_evaluation(session, reservation_id)
        _record_evaluation_error("GH-003", error, started)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error

    rule = RuleResponse(id=persisted.rule_id, version=persisted.rule_version) if persisted.rule_id and persisted.rule_version else None
    evidence = persisted.reconstructed_evidence
    if not isinstance(evidence, GH003Evidence):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored GH-003 evidence is inconsistent")
    evidence_hash = evidence.canonical_hash()
    explanation = build_result_explanation(
        control_id=persisted.control_id,
        rule_id=persisted.rule_id,
        rule_version=persisted.rule_version,
        status=persisted.status,
        evidence=evidence,
        evidence_hash=evidence_hash,
    )
    return GH003EvaluationResponse(
        evaluation_id=str(persisted.id),
        control_id=persisted.control_id,
        rule=rule,
        status=persisted.status.name,
        source=SourceResponse(type=persisted.source_type, repository=persisted.source_repository, branch=persisted.source_branch),
        evidence=GH003EvidenceResponse(
            branch=evidence.branch,
            required_signatures_enabled=evidence.required_signatures_enabled,
            hash=evidence_hash,
        ),
        collected_at=persisted.collected_at.isoformat(),
        evaluated_at=persisted.evaluated_at.isoformat(),
        explanation=explanation,
    )
