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
    if not db_url:
        pytest.fail("DATABASE_URL must be provided for postgres tests")
    
    engine = create_engine(db_url)
    if engine.dialect.name != "postgresql":
        pytest.fail(f"Expected postgresql dialect, got {engine.dialect.name}")
        
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

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
