import os
from typing import Generator
from fastapi import Request

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from securecode.adapters.postgres.models import Base
from securecode.adapters.postgres.repository import PostgresEvaluationRepository
from securecode.ports.evaluation_repository import EvaluationRepository


def _normalize_database_url(url: str) -> str:
    """
    Normalize a database URL to the format expected by SQLAlchemy.

    Some providers (e.g. Heroku, older Supabase connection strings) return
    'postgres://' which SQLAlchemy >= 1.4 does not accept.  This function
    rewrites that prefix to 'postgresql://' while leaving every other URL
    scheme untouched (sqlite://, postgresql+psycopg2://, etc.).
    """
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def _is_postgres_url(url: str) -> bool:
    """Return True if the URL targets a PostgreSQL dialect."""
    return url.startswith("postgresql")


def get_database_url() -> str:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return _normalize_database_url(db_url)


# We will lazily initialize the engine
_engine = None
_SessionLocal = None


def get_engine():
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
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_evaluation_repository(session: Session = None) -> EvaluationRepository:
    # Allows overriding for testing, otherwise relies on get_db_session
    if session is None:
        raise ValueError("Session required")
    return PostgresEvaluationRepository(session)


def get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        # We allow none and it will result in UNKNOWN or 401 later in the adapter
        return None
    return token


from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from securecode.api.security import verify_access_token
from securecode.adapters.postgres.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_db_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = verify_access_token(token)
    if user_id is None:
        raise credentials_exception

    user = session.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allow administration routes only to persisted administrator accounts."""
    if getattr(current_user, "role", "auditor") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    return current_user
