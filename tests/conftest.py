"""Shared pytest fixtures providing hermetic state for API tests."""
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from securecode.adapters.postgres.models import UserSession
from securecode.api.app import app
from securecode.api.dependencies import get_db_session
from securecode.api.security import create_access_token, get_jwt_expire_minutes


def issue_access_token(session, user_id) -> str:
    jti = str(uuid4())
    now = datetime.now(UTC)
    session.add(UserSession(
        id=uuid4(), user_id=user_id, jti=jti, created_at=now,
        expires_at=now + timedelta(minutes=get_jwt_expire_minutes()),
        last_seen_at=now, revoked_at=None, revoked_reason=None,
    ))
    if hasattr(session, "commit"):
        session.commit()
    return create_access_token(str(user_id), jti=jti)


@pytest.fixture(autouse=True)
def clean_api_state(monkeypatch):
    """Restore env, clear dependency overrides, and reset login-rate state."""
    monkeypatch.setenv("APP_ENV", "test")
    if not os.environ.get("DATABASE_URL"):
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    monkeypatch.setenv("LOGIN_MAX_FAILURES", "5")
    monkeypatch.setenv("LOGIN_WINDOW_SECONDS", "900")
    app.dependency_overrides.pop(get_db_session, None)
    yield
    app.dependency_overrides.clear()
