import os
import sys
import json
import subprocess
import platform
from datetime import datetime, timezone
from pathlib import Path

# Add src to sys.path so we can import securecode if this is run directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from securecode.adapters.github import get_gh001_evidence
from securecode.engine.evaluator import evaluate_gh001

def get_git_commit(repo_path: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], 
            cwd=str(repo_path),
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
    except Exception:
        return "unknown"

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("REAL VALIDATION BLOCKED - GITHUB_TOKEN NOT AVAILABLE")
        sys.exit(1)

    repo_root = Path(__file__).parent.parent
    
    # Allow overriding Ground Truth path via environment variable
    env_gt_path = os.environ.get("GROUND_TRUTH_PATH")
    if env_gt_path:
        gt_path = Path(env_gt_path)
    else:
        gt_path = repo_root.parent / "securecode-ground-truth" / "data" / "ground_truth" / "gh001_ground_truth.json"
    
    if not gt_path.exists():
        print(f"ERROR: Ground Truth dataset not found at {gt_path}")
        sys.exit(1)
        
    with open(gt_path, "r", encoding="utf-8") as f:
        gt_data = json.load(f)
        
    cases = gt_data.get("cases", [])
    
    results = []
    matched_count = 0
    mismatched_count = 0
    
    print(f"Starting REAL GitHub validation for {len(cases)} cases...")
    
    for case in cases:
        case_id = case["case_id"]
        repo_full = case["repository"]
        branch = case["branch"]
        expected_status = case["expected_status"]
        
        owner, repo = repo_full.split("/")
        
        try:
            evidence = get_gh001_evidence(owner, repo, branch, token)
            status = evaluate_gh001(evidence)
            actual_status = status.name
        except Exception as e:
            actual_status = f"ERROR: {str(e)}"
            evidence = None
            
        match = (actual_status == expected_status)
        if match:
            matched_count += 1
        else:
            mismatched_count += 1
            
        result = {
            "case_id": case_id,
            "repository": repo_full,
            "branch": branch,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "match": match,
            "required_review_approvals": evidence.required_review_approvals if evidence else None,
            "dismiss_stale_reviews": evidence.dismiss_stale_reviews if evidence else None
        }
        results.append(result)
        
        print(f"[{case_id}] Expected: {expected_status} | Actual: {actual_status} | Match: {match}")

    accuracy = matched_count / len(cases) if cases else 0.0
    
    gt_repo_root = gt_path.parent.parent.parent
    
    artifact = {
        "control": "GH-001",
        "validation_type": "real_github_pilot",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "securecode_commit": get_git_commit(repo_root),
        "ground_truth_commit": get_git_commit(gt_repo_root),
        "python_version": platform.python_version(),
        "cases": results,
        "summary": {
            "total": len(cases),
            "matched": matched_count,
            "mismatched": mismatched_count,
            "accuracy": accuracy
        }
    }
    
    artifacts_dir = repo_root / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    out_file = artifacts_dir / "gh001_real_validation.json"
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
        
    print(f"\nValidation complete. Accuracy: {accuracy*100:.1f}%")
    print(f"Artifact saved to {out_file}")
    
    if mismatched_count > 0:
        print(f"ERROR: {mismatched_count} cases mismatched.")
        sys.exit(1)
        
    sys.exit(0)

if __name__ == "__main__":
    main()
