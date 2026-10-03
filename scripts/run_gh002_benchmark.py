import os
import sys
import json
import subprocess
import platform
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from securecode.models.gh002 import GH002Evidence
from securecode.engine.evaluator import evaluate_gh002

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
    repo_root = Path(__file__).parent.parent
    gt_path = repo_root.parent / "securecode-ground-truth" / "data" / "ground_truth" / "gh002_ground_truth.json"
    
    if not gt_path.exists():
        print(f"ERROR: Ground Truth benchmark dataset not found at {gt_path}")
        sys.exit(1)
        
    with open(gt_path, "r", encoding="utf-8") as f:
        cases = json.load(f)
        
    results = []
    matched_count = 0
    mismatched_count = 0
    
    # Confusion Matrix
    cm = {
        "PASS": {"PASS": 0, "FAIL": 0, "UNKNOWN": 0},
        "FAIL": {"PASS": 0, "FAIL": 0, "UNKNOWN": 0},
        "UNKNOWN": {"PASS": 0, "FAIL": 0, "UNKNOWN": 0},
    }
    
    print(f"Starting GH-002 Benchmark Evaluation on {len(cases)} synthetic cases...")
    
    for case in cases:
        expected = case["status"]
        
        # Instantiate evidence directly from the benchmark dataset
        db = case["evidence"]["default_branch"]
        pe = case["evidence"]["protection_enabled"]
        evidence = GH002Evidence(default_branch=db, protection_enabled=pe)
        
        # Evaluate using production logic
        status = evaluate_gh002(evidence)
        actual = status.name
        
        match = (actual == expected)
        if match:
            matched_count += 1
        else:
            mismatched_count += 1
            
        cm[expected][actual] += 1
        
        results.append({
            "repository": case["repository"],
            "expected_status": expected,
            "actual_status": actual,
            "match": match
        })

    def calc_metrics(cls):
        tp = cm[cls][cls]
        fp = sum(cm[other][cls] for other in cm if other != cls)
        fn = sum(cm[cls][other] for other in cm if other != cls)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {"precision": precision, "recall": recall, "f1": f1}

    metrics = {
        "PASS": calc_metrics("PASS"),
        "FAIL": calc_metrics("FAIL"),
        "UNKNOWN": calc_metrics("UNKNOWN"),
        "overall_accuracy": matched_count / len(cases) if cases else 0.0
    }
    
    gt_repo_root = gt_path.parent.parent.parent
    
    artifact = {
        "benchmark_version": "1.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "securecode_commit": get_git_commit(repo_root),
        "ground_truth_commit": get_git_commit(gt_repo_root),
        "python_version": platform.python_version(),
        "dataset_distribution": {
            "PASS": sum(cm["PASS"].values()),
            "FAIL": sum(cm["FAIL"].values()),
            "UNKNOWN": sum(cm["UNKNOWN"].values())
        },
        "total_cases": len(cases),
        "matched": matched_count,
        "mismatched": mismatched_count,
        "metrics": metrics,
        "confusion_matrix": cm,
        "cases": results
    }
    
    artifacts_dir = repo_root / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    json_out = artifacts_dir / "gh002_benchmark_results.json"
    
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
        
    print(f"\nBenchmark complete. Accuracy: {metrics['overall_accuracy']*100:.1f}%")
    print(f"JSON artifact saved to {json_out}")

if __name__ == "__main__":
    main()
