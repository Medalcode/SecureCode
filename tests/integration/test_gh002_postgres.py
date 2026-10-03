import pytest
import os
from uuid import uuid4
from datetime import datetime, timezone
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from securecode.adapters.postgres.models import Base, EvaluationRecord, EvidenceRecord
from securecode.adapters.postgres.repository import PostgresEvaluationRepository
from securecode.models.gh002 import GH002Evidence
from securecode.engine.evaluator import EvaluationStatus

DB_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DB_URL or "postgresql" not in DB_URL,
    reason="Requires PostgreSQL DATABASE_URL"
)

@pytest.fixture(scope="module")
def engine():
    engine = sqlalchemy.create_engine(DB_URL)
    Base.metadata.create_all(engine)
    yield engine
    # We do not drop tables so artifacts can inspect

@pytest.fixture
def session(engine):
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()

def test_postgres_gh002_round_trip(session):
    repo = PostgresEvaluationRepository(session)
    
    evaluation_id = uuid4()
    evidence_id = uuid4()
    
    evidence = GH002Evidence(default_branch="main", protection_enabled=True)
    collected_at = datetime.now(timezone.utc)
    evaluated_at = datetime.now(timezone.utc)
    
    repo.save_gh002_evaluation(
        evaluation_id=evaluation_id,
        evidence_id=evidence_id,
        evidence=evidence,
        status=EvaluationStatus.PASS,
        source_repository="owner/repo",
        source_branch="main",
        collected_at=collected_at,
        evaluated_at=evaluated_at
    )
    
    retrieved = repo.get_evaluation(evaluation_id)
    assert retrieved is not None
    assert retrieved.control_id == "GH-002"
    assert retrieved.status == EvaluationStatus.PASS
    assert retrieved.reconstructed_evidence.default_branch == "main"
    assert retrieved.reconstructed_evidence.protection_enabled is True
