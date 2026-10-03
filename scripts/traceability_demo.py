import os
from uuid import uuid4
from datetime import datetime, timezone
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from securecode.models.gh001 import GH001Evidence
from securecode.engine.evaluator import evaluate_gh001, EvaluationStatus
from securecode.adapters.postgres.models import Base
from securecode.adapters.postgres.repository import PostgresEvaluationRepository

def main():
    print("--- SECURECODE TRACEABILITY DEMONSTRATION ---")
    
    # 1. Database Setup
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found in environment. Using in-memory SQLite for demonstration.")
        db_url = "sqlite:///:memory:"
    
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    repo = PostgresEvaluationRepository(session)
    
    # 2. Evidence Acquisition (simulated valid input)
    evidence = GH001Evidence(required_review_approvals=2, dismiss_stale_reviews=True)
    collected_at = datetime.now(timezone.utc)
    
    # 3. Deterministic Evaluation
    status = evaluate_gh001(evidence)
    evaluated_at = datetime.now(timezone.utc)
    
    # 4. Persistence
    eval_id = uuid4()
    ev_id = uuid4()
    
    repo.save_gh001_evaluation(
        evaluation_id=eval_id,
        evidence_id=ev_id,
        evidence=evidence,
        status=status,
        source_repository="Medalcode/SecureCode",
        source_branch="main",
        collected_at=collected_at,
        evaluated_at=evaluated_at
    )
    print(f"\n[+] Successfully saved Evaluation ID: {eval_id}")
    
    # 5. Retrieve & Reconstruct
    persisted = repo.get_evaluation(eval_id)
    if not persisted:
        print("[-] Failed to retrieve evaluation!")
        return
        
    print("\n--- RETRIEVED RECORD ---")
    print(f"Evaluation ID: {persisted.id}")
    print(f"Control:       {persisted.control_id}")
    print(f"Source:        {persisted.source_type}")
    print(f"Repository:    {persisted.source_repository}")
    print(f"Branch:        {persisted.source_branch}")
    print(f"Evidence hash: {persisted.reconstructed_evidence.canonical_hash()}")
    print(f"Status:        {persisted.status.name}")
    print(f"Collected at:  {collected_at.isoformat()}")
    print(f"Evaluated at:  {persisted.evaluated_at.isoformat()}")
    
    # 6. Traceability Verification
    print("\n--- VERIFICATION ---")
    evidence_match = (evidence == persisted.reconstructed_evidence)
    status_match = (status == persisted.status)
    
    print(f"Stored evidence == Reconstructed evidence: {evidence_match}")
    print(f"Stored status   == Original status:        {status_match}")

if __name__ == "__main__":
    main()
