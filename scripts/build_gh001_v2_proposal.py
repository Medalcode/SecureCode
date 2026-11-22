import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from securecode.application.gh001_benchmark import build_metrics, canonical_sha256

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_V1 = REPO_ROOT / "docs" / "benchmark" / "gh001" / "v1" / "gh001_benchmark_105_v1.snapshot.json"
BENCH_ROOT = REPO_ROOT / "docs" / "benchmark" / "gh001"
V1_SNAPSHOT = BENCH_ROOT / "v1" / "gh001_benchmark_105_v1.snapshot.json"
V2_DATASET = BENCH_ROOT / "v2" / "gh001_benchmark_105_v2.proposed.json"
V2_SHA256 = BENCH_ROOT / "v2" / "gh001_benchmark_105_v2.proposed.json.sha256"
V2_PATCH = BENCH_ROOT / "v2" / "gh001_benchmark_105_v2.patch.json"
V2_REPORT = BENCH_ROOT / "v2" / "gh001_v2_change_report.md"
PROPOSAL_DATE = "2026-11-21"
V1_EXPECTED_SHA256 = "8319425d25a1b251f680282495e22a11043093397cf36afcd88a77a1529d7947"
V1_EXPECTED_CASES = 105
V1_EXPECTED_MISMATCHES = 14
V2_OUTPUTS = (V2_DATASET, V2_SHA256, V2_PATCH, V2_REPORT)


def _dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def _ensure_output_target(path: Path) -> None:
    if path.resolve() == V1_SNAPSHOT.resolve():
        raise ValueError(f"Refusing to overwrite immutable v1 snapshot: {path}")
    if path.suffix.lower() != ".json" and path not in V2_OUTPUTS:
        raise ValueError(f"Refusing to write unexpected output path: {path}")


def _verify_v1_snapshot(path: Path) -> bytes:
    if not path.exists():
        raise FileNotFoundError(f"V1 dataset not found: {path}")
    canonical_bytes = _canonical_bytes(path)
    actual_hash = hashlib.sha256(canonical_bytes).hexdigest()
    if actual_hash != V1_EXPECTED_SHA256:
        raise ValueError(
            "V1 snapshot integrity check failed: "
            f"expected {V1_EXPECTED_SHA256}, got {actual_hash} for {path}"
        )
    payload = json.loads(canonical_bytes.decode("utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != V1_EXPECTED_CASES:
        raise ValueError(f"Expected {V1_EXPECTED_CASES} cases in v1 snapshot, found {len(cases) if isinstance(cases, list) else 'invalid'}")
    if len({case["case_id"] for case in cases}) != len(cases):
        raise ValueError("Duplicate case_id in V1 dataset")
    return canonical_bytes


def _reason(evidence: dict) -> str:
    approvals = evidence.get("required_review_approvals")
    dismiss = evidence.get("dismiss_stale_reviews")
    if dismiss is False and approvals is None:
        return "dismiss_stale_reviews=false es incumplimiento comprobado; FAIL prevalece sobre aprobaciones ausentes"
    if approvals in (0, 1) and dismiss is None:
        return f"required_review_approvals={approvals} es incumplimiento comprobado; FAIL prevalece sobre descarte ausente"
    raise ValueError(f"Unexpected discrepancy evidence: {evidence!r}")


def build(v1_path: Path) -> dict:
    v1_path = v1_path.resolve()
    if v1_path != V1_SNAPSHOT.resolve():
        raise ValueError(
            "GH-001 v1 is immutable; build must read from "
            f"{V1_SNAPSHOT.as_posix()} and may only emit v2 proposal artifacts"
        )

    v1_bytes = _verify_v1_snapshot(v1_path)
    v1 = json.loads(v1_bytes.decode("utf-8"))
    cases = v1["cases"]

    v1_metrics = build_metrics(cases)
    discrepancies = v1_metrics["mismatches"]
    if len(discrepancies) != V1_EXPECTED_MISMATCHES:
        raise ValueError(f"Expected {V1_EXPECTED_MISMATCHES} discrepancies, found {len(discrepancies)}")
    if any(item["expected_status"] != "UNKNOWN" or item["actual_status"] != "FAIL" for item in discrepancies):
        raise ValueError("Unexpected discrepancy classification")

    v2_cases = copy.deepcopy(cases)
    changed_ids = [item["case_id"] for item in discrepancies]
    for case in v2_cases:
        if case["case_id"] in changed_ids:
            case["expected_status"] = "FAIL"

    v2_metrics = build_metrics(v2_cases)
    if v2_metrics["mismatched"] != 0:
        raise ValueError("Proposed V2 still has mismatches against the engine")
    if len(v2_cases) != V1_EXPECTED_CASES or len({case["case_id"] for case in v2_cases}) != V1_EXPECTED_CASES:
        raise ValueError("Proposed V2 must preserve 105 unique case IDs")

    v2_payload = {
        "schema_version": "2.0",
        "control": "GH-001",
        "dataset_version": "2.0-proposed",
        "status": "PROPOSED_NOT_ADOPTED",
        "created_at": PROPOSAL_DATE,
        "semantics_contract": "docs/specs/EVALUATION-SEMANTICS.md",
        "and_precedence": "FAIL > UNKNOWN > PASS",
        "source_dataset": {
            "path": "docs/benchmark/gh001/v1/gh001_benchmark_105_v1.snapshot.json",
            "dataset_version": v1.get("schema_version", "1.0"),
            "file_sha256": V1_EXPECTED_SHA256,
        },
        "case_count": len(v2_cases),
        "status_distribution": v2_metrics["expected_distribution"],
        "cases_canonical_sha256": canonical_sha256(v2_cases),
        "changes_from_v1": len(changed_ids),
        "cases": v2_cases,
    }
    for output in V2_OUTPUTS:
        _ensure_output_target(output)
    _dump_json(V2_DATASET, v2_payload)
    v2_hash = _file_sha256(V2_DATASET)
    V2_SHA256.write_text(f"{v2_hash}\n", encoding="utf-8")

    index_by_id = {case["case_id"]: index for index, case in enumerate(v2_cases)}
    patch = [
        {
            "op": "replace",
            "path": f"/cases/{index_by_id[case_id]}/expected_status",
            "value": "FAIL",
        }
        for case_id in sorted(changed_ids)
    ]
    _dump_json(V2_PATCH, patch)

    lines = [
        "# GH-001 benchmark v2 propuesto",
        "",
        "Artefacto propuesto, no adoptado oficialmente. El dataset canónico externo permanece intacto.",
        "",
        f"- Fecha: {PROPOSAL_DATE}",
        f"- Casos: {len(v2_cases)}",
        f"- SHA-256 de v1: `{v2_payload['source_dataset']['file_sha256']}`",
        f"- SHA-256 del archivo v2 propuesto: `{v2_hash}`",
        f"- SHA-256 canónico de casos v2: `{v2_payload['cases_canonical_sha256']}`",
        f"- Distribución v1: PASS={v1_metrics['expected_distribution']['PASS']}, FAIL={v1_metrics['expected_distribution']['FAIL']}, UNKNOWN={v1_metrics['expected_distribution']['UNKNOWN']}",
        f"- Distribución v2: PASS={v2_metrics['expected_distribution']['PASS']}, FAIL={v2_metrics['expected_distribution']['FAIL']}, UNKNOWN={v2_metrics['expected_distribution']['UNKNOWN']}",
        f"- Coincidencias v1: {v1_metrics['matched']}/{len(cases)}",
        f"- Coincidencias v2: {v2_metrics['matched']}/{len(v2_cases)}",
        "",
        "## Cambios exactos",
        "",
        "| ID | Evidencia | v1 | Motor | v2 propuesto | Justificación |",
        "|---|---|---|---|---|---|",
    ]
    for item in sorted(discrepancies, key=lambda row: row["case_id"]):
        evidence = item["evidence"] or {}
        lines.append(
            f"| {item['case_id']} | A={evidence.get('required_review_approvals')}, D={evidence.get('dismiss_stale_reviews')} | "
            f"{item['expected_status']} | {item['actual_status']} | FAIL | {_reason(evidence)} |"
        )

    lines.extend([
        "",
        "## Procedimiento de incorporación",
        "",
        "1. Revisar y aprobar `docs/specs/EVALUATION-SEMANTICS.md` como contrato normativo.",
        "2. Aplicar `gh001_benchmark_105_v2.patch.json` sobre una copia del dataset v1.",
        "3. Verificar identificadores, evidencias y hash canónico contra `gh001_benchmark_105_v2.proposed.json`.",
        "4. Publicar v2 en `securecode-ground-truth` con nueva versión de oráculo, manifiesto y hashes.",
        "5. Actualizar la documentación de resultados de GH-001 sin reescribir los dictámenes históricos.",
        "",
        "Este artefacto no declara adopción oficial de v2.",
        "",
    ])
    _ensure_output_target(V2_REPORT)
    V2_REPORT.write_text("\n".join(lines), encoding="utf-8")

    return {
        "v1_matched": v1_metrics["matched"],
        "v1_mismatched": v1_metrics["mismatched"],
        "v2_matched": v2_metrics["matched"],
        "v2_mismatched": v2_metrics["mismatched"],
        "v1_sha256": v2_payload["source_dataset"]["file_sha256"],
        "v2_sha256": v2_hash,
        "changed_ids": sorted(changed_ids),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the proposed GH-001 benchmark v2 from immutable v1")
    parser.add_argument("--v1", type=Path, default=DEFAULT_V1)
    args = parser.parse_args()
    result = build(args.v1)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
