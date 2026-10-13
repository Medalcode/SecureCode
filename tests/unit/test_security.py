import os
import pytest
from datetime import timedelta
import time
from securecode.api.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token
)
from argon2.exceptions import VerifyMismatchError

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"
os.environ["JWT_ALGORITHM"] = "HS256"

def test_password_hashing():
    password = "SuperSecretPassword123"
    hashed = hash_password(password)
    
    # Verify the hash starts with typical argon2id identifier
    assert hashed.startswith("$argon2id$")
    assert hashed != password
    
    # Valid password passes
    assert verify_password(password, hashed) is True
    
    # Invalid password fails
    assert verify_password("WrongPassword", hashed) is False
    
    # Same password produces a different hash (salting)
    hashed2 = hash_password(password)
    assert hashed != hashed2
    assert verify_password(password, hashed2) is True

def test_jwt_creation_and_verification():
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    
    # Create token
    token = create_access_token(user_id)
    assert token is not None
    assert isinstance(token, str)
    
    # Verify token
    decoded_user_id = verify_access_token(token)
    assert decoded_user_id == user_id

def test_jwt_invalid_token():
    assert verify_access_token("not.a.real.jwt") is None

def test_jwt_expired_token(monkeypatch):
    user_id = "test-user-id"
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "-1")
    
    token = create_access_token(user_id)
    # The token is immediately expired
    decoded = verify_access_token(token)
    assert decoded is None

def test_jwt_tampered_token():
    user_id = "test-user"
    token = create_access_token(user_id)
    # Tamper with payload
    tampered_token = token[:-5] + "aaaaa"
    
    decoded = verify_access_token(tampered_token)
    assert decoded is None
