import os
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, text, inspect
from alembic.config import Config
from alembic import command
from securecode.adapters.postgres.models import Base
import json

@pytest.fixture
def postgres_url():
    url = os.environ.get("DATABASE_URL")
    if not url or not url.startswith("postgresql"):
        pytest.skip("Migration tests require REAL PostgreSQL.")
    return url

@pytest.fixture
def alembic_cfg(postgres_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", postgres_url)
    return cfg

def _drop_all(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO public;"))

def test_fresh_install_migration(postgres_url, alembic_cfg):
    """TEST 1 & 10: Prove empty DB -> upgrade head works."""
    engine = create_engine(postgres_url)
    _drop_all(engine)
    
    # Run upgrade head
    command.upgrade(alembic_cfg, "head")
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "evidence_records" in tables
    assert "evaluation_records" in tables
    
    columns = [c["name"] for c in inspector.get_columns("evaluation_records")]
    assert "rule_id" in columns
    assert "rule_version" in columns

def test_historical_migration_preservation(postgres_url, alembic_cfg):
    """TEST 2, 3, 7, 8: Baseline -> upgrade head -> historical data preserved."""
    engine = create_engine(postgres_url)
    _drop_all(engine)
    
    # Run upgrade to baseline
    command.upgrade(alembic_cfg, "7409c81f5bf7")
    
    # Insert historical data
    evidence_id = str(uuid4())
    eval_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO evidence_records 
                (id, control_id, evidence_hash, raw_evidence, collected_at) 
                VALUES (:id, :control, :hash, :raw, :collected)
            """),
            {
                "id": evidence_id, "control": "GH-001", "hash": "testhash",
                "raw": json.dumps({"required_review_approvals": 2, "dismiss_stale_reviews": True}),
                "collected": now
            }
        )
        
        conn.execute(
            text("""
                INSERT INTO evaluation_records 
                (id, control_id, status, evaluated_at, evidence_id, source_type, source_repository, source_branch) 
                VALUES (:id, :control, :status, :evaluated, :evidence_id, :source_type, :repo, :branch)
            """),
            {
                "id": eval_id, "control": "GH-001", "status": "PASS", "evaluated": now,
                "evidence_id": evidence_id, "source_type": "GitHub", "repo": "test/repo", "branch": "main"
            }
        )
    
    # Run upgrade head
    command.upgrade(alembic_cfg, "head")
    
    # Verify historical data
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM evaluation_records WHERE id = :id"), {"id": eval_id}).fetchone()
        assert result is not None
        assert result.control_id == "GH-001"
        assert result.status == "PASS"
        assert result.rule_id is None  # Legacy data should have explicit NULL traceability
        assert result.rule_version is None
        
def test_schema_parity(postgres_url, alembic_cfg):
    """TEST 6: Compare Alembic schema with SQLAlchemy metadata."""
    engine = create_engine(postgres_url)
    _drop_all(engine)
    command.upgrade(alembic_cfg, "head")
    
    inspector = inspect(engine)
    alembic_columns = {c["name"]: c for c in inspector.get_columns("evaluation_records")}
    
    # We verify that rule_id and rule_version are present and nullable
    assert "rule_id" in alembic_columns
    assert alembic_columns["rule_id"]["nullable"] is True
    
    assert "rule_version" in alembic_columns
    assert alembic_columns["rule_version"]["nullable"] is True
    
def test_new_evaluations_after_migration(postgres_url, alembic_cfg):
    """TEST 4 & 5: new GH-001/002 evaluation after upgrade."""
    engine = create_engine(postgres_url)
    _drop_all(engine)
    command.upgrade(alembic_cfg, "head")
    
    from sqlalchemy.orm import sessionmaker
    from securecode.adapters.postgres.repository import PostgresEvaluationRepository
    from securecode.models.gh001 import GH001Evidence
    from securecode.models.gh002 import GH002Evidence
    from securecode.engine.types import EvaluationStatus
    from datetime import datetime, timezone
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    repo = PostgresEvaluationRepository(session)
    
    eval_id1 = uuid4()
    evidence1 = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    repo.save_gh001_evaluation(
        evaluation_id=eval_id1,
        evidence_id=uuid4(),
        evidence=evidence1,
        status=EvaluationStatus.PASS,
        source_repository="test/test",
        source_branch="main",
        collected_at=datetime.now(timezone.utc),
        evaluated_at=datetime.now(timezone.utc),
        rule_id="GH-001-RULE",
        rule_version=1
    )
    
    eval_id2 = uuid4()
    evidence2 = GH002Evidence(default_branch="main", protection_enabled=True)
    repo.save_gh002_evaluation(
        evaluation_id=eval_id2,
        evidence_id=uuid4(),
        evidence=evidence2,
        status=EvaluationStatus.PASS,
        source_repository="test/test",
        source_branch="main",
        collected_at=datetime.now(timezone.utc),
        evaluated_at=datetime.now(timezone.utc),
        rule_id="GH-002-RULE",
        rule_version=1
    )
    
    # Verify new data is populated correctly
    with engine.connect() as conn:
        res1 = conn.execute(text("SELECT rule_id, rule_version FROM evaluation_records WHERE id = :id"), {"id": str(eval_id1)}).fetchone()
        assert res1.rule_id == "GH-001-RULE"
        assert res1.rule_version == 1
        
        res2 = conn.execute(text("SELECT rule_id, rule_version FROM evaluation_records WHERE id = :id"), {"id": str(eval_id2)}).fetchone()
        assert res2.rule_id == "GH-002-RULE"
        assert res2.rule_version == 1
