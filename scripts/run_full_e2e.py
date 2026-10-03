import os
import sys
import json
import platform
from datetime import datetime, timezone

import fastapi
import sqlalchemy
from fastapi.testclient import TestClient

from securecode.api.app import app
from securecode.adapters.postgres.models import EvaluationRecord, EvidenceRecord, Base
from securecode.api.dependencies import get_db_session

def main():
    token = os.environ.get("VALIDATION_GITHUB_TOKEN")
    if not token:
        print("Error: VALIDATION_GITHUB_TOKEN is missing.")
        sys.exit(1)
        
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or "postgresql" not in db_url:
        print("Error: DATABASE_URL must be a valid PostgreSQL connection string.")
        sys.exit(1)
        
    # We set GITHUB_TOKEN so the API will pick it up
    os.environ["GITHUB_TOKEN"] = token
        
    engine = sqlalchemy.create_engine(db_url)
    SessionLocal = sqlalchemy.orm.sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Initialize schema
    Base.metadata.create_all(engine)
    
    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
            
    app.dependency_overrides[get_db_session] = override_get_db
    client = TestClient(app)
    
    cases = [
        {"name": "PASS", "branch": "gh001-pass", "expected": "PASS"},
        {"name": "FAIL", "branch": "gh001-fail-approvals", "expected": "FAIL"},
        {"name": "UNKNOWN", "branch": "gh001-unknown-noprot", "expected": "UNKNOWN"},
    ]
    
    results = {}
    matched_count = 0
    mismatched_count = 0
    
    for case in cases:
        status_name = case["name"]
        expected = case["expected"]
        
        response = client.post("/api/v1/evaluations/gh-001", json={
            "owner": "Medalcode",
            "repository": "securecode-ground-truth",
            "branch": case["branch"]
        })
        
        http_status = response.status_code
        if http_status != 200:
            print(f"[{status_name}] Failed HTTP: {http_status} - {response.text}")
            results[status_name] = {
                "expected_status": expected,
                "http_status": http_status,
                "actual_status": "ERROR",
                "persisted": False,
                "trace_verified": False,
                "timestamps_verified": False
            }
            mismatched_count += 1
            continue
            
        data = response.json()
        actual_status = data["status"]
        
        if actual_status == expected:
            matched_count += 1
        else:
            mismatched_count += 1
            
        # Verify Persistence & Timestamps
        eval_id = data["evaluation_id"]
        
        with SessionLocal() as db_session:
            eval_record = db_session.query(EvaluationRecord).filter_by(id=eval_id).first()
            if not eval_record:
                persisted = False
                trace_verified = False
                timestamps_verified = False
            else:
                persisted = True
                
                # Check DB traces match HTTP
                trace_verified = (
                    eval_record.status == actual_status and
                    eval_record.source_branch == case["branch"] and
                    eval_record.evidence.evidence_hash == data["evidence"]["hash"]
                )
                
                # Timestamp validation
                # Ensure collected_at <= evaluated_at, and they match the response exactly
                api_collected = datetime.fromisoformat(data["collected_at"])
                api_evaluated = datetime.fromisoformat(data["evaluated_at"])
                
                db_collected = eval_record.evidence.collected_at
                db_evaluated = eval_record.evaluated_at
                
                timestamps_verified = (
                    api_collected == db_collected and
                    api_evaluated == db_evaluated and
                    db_collected <= db_evaluated
                )
        
        results[status_name] = {
            "expected_status": expected,
            "http_status": http_status,
            "actual_status": actual_status,
            "persisted": persisted,
            "trace_verified": trace_verified,
            "timestamps_verified": timestamps_verified
        }

    try:
        import subprocess
        securecode_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        securecode_commit = "unknown"
        
    pg_version = "unknown"
    with engine.connect() as conn:
        pg_version = conn.execute(sqlalchemy.text("SHOW server_version;")).scalar()

    artifact = {
        "validation_type": "gh001_full_real_e2e",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "securecode_commit": securecode_commit,
        "ground_truth_commit": "main", # Cannot easily extract remote sha securely here
        "python_version": platform.python_version(),
        "fastapi_version": fastapi.__version__,
        "sqlalchemy_version": sqlalchemy.__version__,
        "postgresql_version": pg_version,
        "external_services": {
            "github": {"real": True},
            "postgresql": {"real": True}
        },
        "cases": results,
        "summary": {
            "cases": len(cases),
            "matched": matched_count,
            "mismatched": mismatched_count,
            "persistence_verified": all(r["persisted"] for r in results.values()),
            "timestamp_semantics_verified": all(r["timestamps_verified"] for r in results.values())
        }
    }
    
    os.makedirs("artifacts", exist_ok=True)
    out_path = os.path.join("artifacts", "gh001_full_e2e_validation.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
        
    print(f"Artifact successfully written to {out_path}")
    
    if mismatched_count > 0 or not artifact["summary"]["persistence_verified"] or not artifact["summary"]["timestamp_semantics_verified"]:
        sys.exit(1)

if __name__ == "__main__":
    main()
