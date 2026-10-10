import os
import pytest
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from securecode.adapters.postgres.models import Base, EvaluationRecord, EvidenceRecord
from securecode.adapters.postgres.repository import PostgresEvaluationRepository
from securecode.models.gh001 import GH001Evidence
from securecode.engine.evaluator import EvaluationStatus

pytestmark = pytest.mark.postgres

@pytest.fixture(scope="session")
def engine():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or "sqlite" in db_url:
        if os.environ.get("REQUIRE_POSTGRES_TESTS") == "1":
            pytest.fail("DATABASE_URL must be provided for postgres tests in CI")
        else:
            pytest.skip("REAL POSTGRESQL VALIDATED - BLOCKED (DATABASE_URL not configured for Postgres)")
    
    engine = create_engine(db_url)
    if engine.dialect.name != "postgresql":
        pytest.fail(f"Expected postgresql dialect, got {engine.dialect.name}")
        
    Base.metadata.create_all(engine)
    yield engine

@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def repo(session):
    return PostgresEvaluationRepository(session)

def test_dialect_verification(engine):
    assert engine.dialect.name == "postgresql"

def test_postgres_schema_creation(engine):
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "evidence_records" in tables
    assert "evaluation_records" in tables
    
    # Check JSONB
    evidence_columns = {col["name"]: type(col["type"]).__name__ for col in inspector.get_columns("evidence_records")}
    assert evidence_columns["raw_evidence"] == "JSONB"
    
    # Check UUID
    assert evidence_columns["id"] == "UUID"

def test_persist_and_retrieve_pass(repo):
    eval_id = uuid4()
    ev_id = uuid4()
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    
    repo.save_gh001_evaluation(
        evaluation_id=eval_id,
        evidence_id=ev_id,
        evidence=evidence,
        status=EvaluationStatus.PASS,
        source_repository="owner/repo",
        source_branch="main",
        collected_at=datetime.now(timezone.utc),
        evaluated_at=datetime.now(timezone.utc)
    )
    
    persisted = repo.get_evaluation(eval_id)
    assert persisted is not None
    assert persisted.status == EvaluationStatus.PASS
    assert persisted.reconstructed_evidence == evidence
    assert persisted.reconstructed_evidence.canonical_hash() == evidence.canonical_hash()

def test_persist_and_retrieve_fail(repo):
    eval_id = uuid4()
    ev_id = uuid4()
    evidence = GH001Evidence(required_review_approvals=0, dismiss_stale_reviews=False)
    
    repo.save_gh001_evaluation(
        evaluation_id=eval_id,
        evidence_id=ev_id,
        evidence=evidence,
        status=EvaluationStatus.FAIL,
        source_repository="owner/repo",
        source_branch="main",
        collected_at=datetime.now(timezone.utc),
        evaluated_at=datetime.now(timezone.utc)
    )
    
    persisted = repo.get_evaluation(eval_id)
    assert persisted is not None
    assert persisted.status == EvaluationStatus.FAIL
    assert persisted.reconstructed_evidence == evidence
    assert persisted.reconstructed_evidence.canonical_hash() == evidence.canonical_hash()

def test_persist_and_retrieve_unknown(repo):
    eval_id = uuid4()
    ev_id = uuid4()
    evidence = GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
    
    repo.save_gh001_evaluation(
        evaluation_id=eval_id,
        evidence_id=ev_id,
        evidence=evidence,
        status=EvaluationStatus.UNKNOWN,
        source_repository="owner/repo",
        source_branch="main",
        collected_at=datetime.now(timezone.utc),
        evaluated_at=datetime.now(timezone.utc)
    )
    
    persisted = repo.get_evaluation(eval_id)
    assert persisted is not None
    assert persisted.status == EvaluationStatus.UNKNOWN
    assert persisted.reconstructed_evidence == evidence
    assert persisted.reconstructed_evidence.canonical_hash() == evidence.canonical_hash()

def test_atomic_transaction_rollback(repo, session):
    eval_id = uuid4()
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    
    repo.save_gh001_evaluation(
        evaluation_id=eval_id,
        evidence_id=uuid4(),
        evidence=evidence,
        status=EvaluationStatus.PASS,
        source_repository="owner/repo",
        source_branch="main",
        collected_at=datetime.now(timezone.utc),
        evaluated_at=datetime.now(timezone.utc)
    )
    
    # Force failure
    with pytest.raises(RuntimeError):
        repo.save_gh001_evaluation(
            evaluation_id=eval_id,  # Duplicate PK
            evidence_id=uuid4(),
            evidence=evidence,
            status=EvaluationStatus.FAIL,
            source_repository="owner/repo",
            source_branch="main",
            collected_at=datetime.now(timezone.utc),
            evaluated_at=datetime.now(timezone.utc)
        )
        
    # Prove no partial state exists
    count = session.query(EvaluationRecord).filter_by(id=eval_id, status="FAIL").count()
    assert count == 0

def test_foreign_key_enforcement(session):
    eval_record = EvaluationRecord(
        id=uuid4(),
        control_id="GH-001",
        status="PASS",
        evaluated_at=datetime.now(timezone.utc),
        evidence_id=uuid4(),  # Random UUID, no corresponding evidence record
        source_type="GitHub",
        source_repository="owner/repo",
        source_branch="main"
    )
    
    session.add(eval_record)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

from fastapi.testclient import TestClient
from unittest.mock import patch
from securecode.api.app import app
from securecode.api.dependencies import get_db_session
from securecode.adapters.postgres.models import User
from securecode.api.security import hash_password, create_access_token

def test_api_postgres_integration(engine, session, monkeypatch):
    # Ensure JWT secrets exist for this test
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")

    # Setup valid test user
    test_user_id = uuid4()
    test_user = User(
        id=test_user_id,
        username=f"integration_user_{uuid4().hex[:12]}",
        password_hash=hash_password("securepassword"),
        active=True,
        created_at=datetime.now(timezone.utc)
    )
    session.add(test_user)
    session.commit()

    # Generate JWT token
    token = create_access_token(str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # Override FastAPI dependency to use our Postgres test session
    app.dependency_overrides[get_db_session] = lambda: session
    
    try:
        client = TestClient(app)
        
        # We only mock the external boundary (GitHub)
        with patch("securecode.application.evaluate_and_store.get_gh001_evidence") as mock_get_evidence:
            mock_get_evidence.return_value = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
            
            response = client.post("/api/v1/evaluations/gh-001", json={
                "owner": "Medalcode",
                "repository": "securecode",
                "branch": "main"
            }, headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "PASS"
            assert data["source"]["repository"] == "Medalcode/securecode"
            assert data["evidence"]["required_review_approvals"] == 2
            
            # Verify it actually reached the database
            eval_id = data["evaluation_id"]
            record = session.query(EvaluationRecord).filter_by(id=eval_id).first()
            assert record is not None
            assert record.status == "PASS"
            assert record.requested_by_user_id == test_user.id
            
    finally:
        app.dependency_overrides.pop(get_db_session, None)
