import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from securecode.application.gh001_benchmark import build_metrics, canonical_sha256


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SecureCode engine against a GH-001 dataset")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw = args.dataset.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    cases = payload["cases"]
    metrics = build_metrics(cases)

    artifact = {
        "benchmark_label": args.label,
        "dataset_path": str(args.dataset),
        "dataset_version": payload.get("dataset_version", payload.get("schema_version", "unknown")),
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "cases_canonical_sha256": canonical_sha256(cases),
        "semantics_contract": "docs/specs/EVALUATION-SEMANTICS.md",
        "generated_by": "scripts/run_gh001_dataset_benchmark.py",
        **metrics,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "label": args.label,
                "total_cases": artifact["total_cases"],
                "matched": artifact["matched"],
                "mismatched": artifact["mismatched"],
                "overall_accuracy": artifact["overall_accuracy"],
                "expected_distribution": artifact["expected_distribution"],
                "actual_distribution": artifact["actual_distribution"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
