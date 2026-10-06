import os
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4

from securecode.api.app import app
from securecode.api.dependencies import get_db_session
from securecode.adapters.postgres.models import User
from securecode.api.security import hash_password

os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["JWT_ALGORITHM"] = "HS256"

class DummyUser:
    def __init__(self, id, username, password_hash, active):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.active = active

mock_user_id = uuid4()
mock_user = DummyUser(
    id=mock_user_id,
    username="testuser",
    password_hash=hash_password("correctpassword"),
    active=True
)

inactive_user_id = uuid4()
inactive_user = DummyUser(
    id=inactive_user_id,
    username="inactiveuser",
    password_hash=hash_password("correctpassword"),
    active=False
)

def mock_session():
    class MockQuery:
        def __init__(self, model):
            self.model = model
            self.filters = []
            
        def filter(self, *args):
            self.filters.extend(args)
            return self
            
        def first(self):
            if not self.filters:
                return None
            
            # Inspect the SQLAlchemy expression tree
            expr = self.filters[0]
            val = getattr(getattr(expr, "right", None), "value", None)
            
            # Fallback if it's an ID equality
            if val is None:
                # might be UUID comparison
                val = getattr(getattr(expr, "right", None), "value", None)
            
            if str(val) == "testuser":
                return mock_user
            if str(val) == "inactiveuser":
                return inactive_user
            if str(val) == str(mock_user_id):
                return mock_user
            if str(val) == str(inactive_user_id):
                return inactive_user
            return None

    class _MockSession:
        def query(self, model):
            return MockQuery(model)

    return _MockSession()

import pytest

@pytest.fixture(autouse=True)
def setup_auth_mock_session():
    app.dependency_overrides[get_db_session] = mock_session
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

def test_login_success():
    response = client.post("/api/v1/auth/token", data={
        "username": "testuser",
        "password": "correctpassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_invalid_password():
    response = client.post("/api/v1/auth/token", data={
        "username": "testuser",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_login_invalid_username():
    response = client.post("/api/v1/auth/token", data={
        "username": "unknownuser",
        "password": "correctpassword"
    })
    assert response.status_code == 401

def test_login_inactive_user():
    response = client.post("/api/v1/auth/token", data={
        "username": "inactiveuser",
        "password": "correctpassword"
    })
    assert response.status_code == 400
    assert "Inactive user" in response.json()["detail"]

def test_protected_endpoints_reject_unauthenticated():
    response = client.post("/api/v1/evaluations/gh-001", json={
        "owner": "Medalcode",
        "repository": "repo",
        "branch": "main"
    })
    assert response.status_code == 401
    
    response = client.post("/api/v1/evaluations/gh-002", json={
        "owner": "Medalcode",
        "repository": "repo"
    })
    assert response.status_code == 401
