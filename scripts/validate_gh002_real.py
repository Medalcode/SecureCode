import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from securecode.adapters.github import get_gh002_evidence
from securecode.engine.evaluator import evaluate_gh002

def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("VALIDATION_GITHUB_TOKEN")
    
    # We will just do public repos for pilot, some might need token
    cases = [
        {"owner": "Medalcode", "repo": "SecureCode", "expected": "PASS"}, # Usually protected if it's main repo (or we assume)
        {"owner": "torvalds", "repo": "linux", "expected": "FAIL"}, # Just an example, though likely needs token
    ]
    
    print("GH-002 Real GitHub Pilot Validation")
    print(f"Token present: {'Yes' if token else 'No'}")
    
    results = []
    
    for case in cases:
        owner = case["owner"]
        repo = case["repo"]
        
        try:
            evidence = get_gh002_evidence(owner, repo, token)
            status = evaluate_gh002(evidence)
            print(f"[{owner}/{repo}] Expected: {case.get('expected', '?')} -> Actual: {status.name}")
            results.append({"repo": f"{owner}/{repo}", "actual": status.name, "evidence": evidence})
        except Exception as e:
            print(f"[{owner}/{repo}] Error: {e}")
            
    print("\nPilot completed.")

if __name__ == "__main__":
    main()
