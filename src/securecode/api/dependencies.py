import os
from typing import Generator
from fastapi import Request

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from securecode.adapters.postgres.models import Base
from securecode.adapters.postgres.repository import PostgresEvaluationRepository
from securecode.ports.evaluation_repository import EvaluationRepository

def get_database_url() -> str:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return db_url

# We will lazily initialize the engine
_engine = None
_SessionLocal = None

def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(get_database_url())
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
