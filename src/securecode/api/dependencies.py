import hashlib
import hmac
import os
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from securecode.adapters.postgres.repository import PostgresEvaluationRepository
from securecode.ports.evaluation_repository import EvaluationRepository


def _normalize_database_url(url: str) -> str:
    """
    Normalize a database URL to the format expected by SQLAlchemy.

    Some providers return ``postgres://`` or a bare ``postgresql://`` URL.
    The production image intentionally ships ``psycopg2-binary`` (not the
    separate psycopg v3 package), so PostgreSQL URLs must explicitly select
    the matching SQLAlchemy dialect.  Other schemes stay untouched.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def _is_postgres_url(url: str) -> bool:
    """Return True if the URL targets a PostgreSQL dialect."""
    return url.startswith("postgresql")


def get_database_url() -> str:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    # Secret-manager CLI input can retain a terminal newline. Never pass it to
    # SQLAlchemy because query values such as sslmode become invalid.
    return _normalize_database_url(db_url.strip())


# We will lazily initialize the engine
_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        db_url = get_database_url()

        if _is_postgres_url(db_url):
            # pool_pre_ping: validates that connections retrieved from the pool
            # are still alive before use.  Critical for Cloud Run / serverless
            # environments where the PostgreSQL server (e.g. Supabase) may have
            # closed idle TCP connections while the container was throttled.
            #
            # pool_recycle: forces SQLAlchemy to discard and re-open connections
            # older than 300 s, preventing stale-connection errors after
            # prolonged inactivity periods common in Cloud Run.
            _engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args={"connect_timeout": 2},
            )
        else:
            # SQLite (used in tests and local development): keep defaults.
            # pool_pre_ping and pool_recycle are not needed and may cause
            # incompatibilities with SQLite's single-writer model.
            _engine = create_engine(db_url)

        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        # Note: We do not call drop_all or create_all here. Schema management
        # is outside the scope of API route execution.
    return _engine


def get_db_session() -> Generator[Session, None, None]:
    get_engine()  # Ensure initialization
    session_factory = _SessionLocal
    if session_factory is None:  # Defensive guard for static analysis and startup failures.
        raise RuntimeError("Database session factory is not initialized")
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_evaluation_repository(session: Session | None = None) -> EvaluationRepository:
    # Allows overriding for testing, otherwise relies on get_db_session
    if session is None:
        raise ValueError("Session required")
    return PostgresEvaluationRepository(session)


def get_github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        # We allow none and it will result in UNKNOWN or 401 later in the adapter
        return None
    return token


from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from securecode.adapters.postgres.models import User, UserSession
from securecode.api.security import decode_access_token
from securecode.domain.roles import is_platform_admin

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

SESSION_COOKIE_NAME = "securecode_session"
CSRF_COOKIE_NAME = "securecode_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user: User
    jti: str
    mode: str


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _credentials_exception(mode: str) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if mode == "bearer" else None
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers=headers,
    )


def _same_origin(origin: str, request: Request) -> bool:
    parsed = urlparse(origin)
    return (
        parsed.scheme == request.url.scheme
        and parsed.hostname == request.url.hostname
        and (parsed.port or (443 if parsed.scheme == "https" else 80))
        == (request.url.port or (443 if request.url.scheme == "https" else 80))
    )


def require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin or not _same_origin(origin, request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origen no permitido")


def _validate_csrf(request: Request, user_session: UserSession) -> None:
    require_same_origin(request)
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(CSRF_HEADER_NAME)
    if not csrf_cookie or not csrf_header:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF requerido")
    if not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF inválido")
    stored_hash = getattr(user_session, "csrf_token_hash", None)
    if not stored_hash:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sesión sin protección CSRF")
    expected_hash = hashlib.sha256(csrf_cookie.encode()).hexdigest()
    if not hmac.compare_digest(str(stored_hash), expected_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF inválido")


def get_authenticated_principal(
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
) -> AuthenticatedPrincipal:
    authorization = request.headers.get("authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise _credentials_exception("bearer")
        mode = "bearer"
        credential = token.strip()
    else:
        mode = "cookie"
        credential = request.cookies.get(SESSION_COOKIE_NAME, "")

    if not credential:
        raise _credentials_exception(mode)
    payload = decode_access_token(credential)
    if payload is None:
        raise _credentials_exception(mode)

    try:
        user_uuid = UUID(payload.sub)
    except (TypeError, ValueError):
        raise _credentials_exception(mode) from None

    user_session = session.query(UserSession).filter(
        UserSession.jti == payload.jti,
        UserSession.user_id == user_uuid,
        UserSession.revoked_at.is_(None),
    ).first()
    if user_session is None or _as_utc(user_session.expires_at) <= datetime.now(UTC):
        raise _credentials_exception(mode)

    if mode == "cookie" and request.method.upper() in _UNSAFE_METHODS:
        _validate_csrf(request, user_session)

    user = session.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise _credentials_exception(mode)
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"} if mode == "bearer" else None,
        )

    request.state.auth_mode = mode
    request.state.session_jti = payload.jti
    return AuthenticatedPrincipal(user=user, jti=payload.jti, mode=mode)


def get_current_user(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
) -> User:
    return principal.user


def require_platform_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Allow global operations only to internal SecureCode operators."""
    if not is_platform_admin(getattr(current_user, "role", None)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform administrator role required")
    return current_user


# Temporary import compatibility for modules not yet moved to the explicit name.
# New routes must depend on ``require_platform_admin``.
require_admin = require_platform_admin
