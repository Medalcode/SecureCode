import pytest
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from securecode.adapters.postgres.models import Base, EvaluationRecord
from securecode.adapters.postgres.repository import PostgresEvaluationRepository
from securecode.models.gh001 import GH001Evidence
from securecode.engine.evaluator import EvaluationStatus

@pytest.fixture
def session():
    """Provides an in-memory SQLite database session for repository testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def repo(session):
    return PostgresEvaluationRepository(session)

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
    assert persisted.control_id == "GH-001"
    assert persisted.reconstructed_evidence == evidence

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

def test_persist_and_retrieve_unknown(repo):
    eval_id = uuid4()
    evidence = GH001Evidence(required_review_approvals=None, dismiss_stale_reviews=None)
    
    repo.save_gh001_evaluation(
        evaluation_id=eval_id,
        evidence_id=uuid4(),
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

def test_atomic_transaction_rollback(repo, session):
    """Test that a failure during persistence rolls back the transaction."""
    eval_id = uuid4()
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    
    # Save normally first
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
    
    # Attempting to save again with the SAME evaluation_id should violate PK constraint
    # causing an atomic rollback.
    with pytest.raises(RuntimeError):
        repo.save_gh001_evaluation(
            evaluation_id=eval_id,
            evidence_id=uuid4(),
            evidence=evidence,
            status=EvaluationStatus.FAIL,
            source_repository="owner/repo",
            source_branch="main",
            collected_at=datetime.now(timezone.utc),
            evaluated_at=datetime.now(timezone.utc)
        )
        
    # Prove no partial state exists from the failed transaction
    count = session.query(EvaluationRecord).filter_by(status="FAIL").count()
    assert count == 0
