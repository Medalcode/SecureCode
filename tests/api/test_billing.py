import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"
os.environ["JWT_ALGORITHM"] = "HS256"

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4

from securecode.api.app import app
from securecode.api.dependencies import get_current_user, get_db_session
from securecode.api.security import create_access_token, hash_password

class DummyUser:
    def __init__(self, id, username, password_hash, active):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.active = active

mock_user_id = uuid4()
mock_user = DummyUser(
    id=mock_user_id,
    username="auditor@empresa.com",
    password_hash=hash_password("Password123!"),
    active=True
)

def test_billing_summary_unauthorized():
    app.dependency_overrides.clear()
    client = TestClient(app)
    resp = client.get("/api/v1/billing/summary")
    assert resp.status_code == 401

def test_billing_summary_authorized():
    client = TestClient(app)
    token = create_access_token(str(mock_user_id))

    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.count.return_value = 11
    mock_query.filter.return_value = mock_filter
    mock_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        resp = client.get(
            "/api/v1/billing/summary",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["app"] == "SECURECODE"
        assert data["title"] == "Centro de Control y Facturación"
        assert data["subscription_plan"]["plan_name"] == "Plan Piloto Institucional"
        assert data["subscription_plan"]["price"] == "$150.000 CLP / mes"
        assert data["monthly_usage"]["consumed"] == 38
        assert data["monthly_usage"]["max"] == 500
        assert len(data["billing_history"]["rows"]) == 2
        assert data["footer"]["audit_id"] == "ID Auditoría: SEC-BLL-2026"
    finally:
        app.dependency_overrides.clear()
