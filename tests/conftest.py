"""Shared pytest fixtures providing hermetic state for API tests."""
import pytest

from securecode.api.app import app
from securecode.api.dependencies import get_db_session


@pytest.fixture(autouse=True)
def clean_api_state(monkeypatch):
    """Restore env, clear dependency overrides, and reset login-rate state."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    monkeypatch.setenv("LOGIN_MAX_FAILURES", "5")
    monkeypatch.setenv("LOGIN_WINDOW_SECONDS", "900")
    monkeypatch.setenv("EMAIL_VERIFICATION_REQUIRED", "false")
    app.dependency_overrides.pop(get_db_session, None)
    yield
    app.dependency_overrides.clear()
