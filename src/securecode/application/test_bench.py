"""
Test Bench (Banco de Pruebas Unitario 'de a 1') Application Service.
Provides Ground Truth test cases and deterministic execution with
sub-millisecond latency tracking and oracle concordance verification.
"""
import time
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.engine.evaluator import evaluate_gh001, evaluate_gh002
from securecode.engine.types import EvaluationStatus

# Ground Truth Dataset Canonical Definition (INACAP ES2 Standard)
GROUND_TRUTH_CASES: List[Dict[str, Any]] = [
    {
        "case_id": "GT-GH001-01",
        "control_id": "GH-001",
        "title": "PASS - Protección Válida y Rigurosa",
        "scenario": "Rama principal con 2 aprobaciones requeridas y descarte de aprobaciones obsoletas activo.",
        "repository": "Medalcode/securecode-ground-truth",
        "branch": "branch-case-1-pass",
        "expected_status": "PASS",
        "evidence_preview": {
            "required_review_approvals": 2,
            "dismiss_stale_reviews": True
        },
        "rationale": "Satisface plenamente la política institucional: approvals >= 2 y dismiss_stale_reviews == True."
    },
    {
        "case_id": "GT-GH001-02",
        "control_id": "GH-001",
        "title": "FAIL - Aprobaciones Insuficientes",
        "scenario": "Rama protegida pero solo exige 1 aprobación (incumple umbral mínimo de 2 revisores).",
        "repository": "Medalcode/securecode-ground-truth",
        "branch": "branch-case-2-fail-low-approvals",
        "expected_status": "FAIL",
        "evidence_preview": {
            "required_review_approvals": 1,
            "dismiss_stale_reviews": True
        },
        "rationale": "Infracción: approvals < 2 (riesgo de commits sin doble revisión colegiada)."
    },
    {
        "case_id": "GT-GH001-03",
        "control_id": "GH-001",
        "title": "FAIL - Revisiones Obsoletas Permitidas",
        "scenario": "Exige 2 aprobaciones pero no invalida revisiones tras nuevos commits (stale reviews permitido).",
        "repository": "Medalcode/securecode-ground-truth",
        "branch": "branch-case-3-fail-no-dismiss",
        "expected_status": "FAIL",
        "evidence_preview": {
            "required_review_approvals": 2,
            "dismiss_stale_reviews": False
        },
        "rationale": "Infracción: dismiss_stale_reviews == False (permite inyectar código no revisado después de un 'LGTM')."
    },
    {
        "case_id": "GT-GH001-04",
        "control_id": "GH-001",
        "title": "FAIL - Doble Infracción de Reglas",
        "scenario": "Exige menos de 2 aprobaciones y además permite mantener revisiones obsoletas.",
        "repository": "Medalcode/securecode-ground-truth",
        "branch": "branch-case-4-fail-both",
        "expected_status": "FAIL",
        "evidence_preview": {
            "required_review_approvals": 1,
            "dismiss_stale_reviews": False
        },
        "rationale": "Violación múltiple de ambos requisitos institucionales de revisión por pares."
    },
    {
        "case_id": "GT-GH001-05",
        "control_id": "GH-001",
        "title": "UNKNOWN - Ausencia Total de Protección",
        "scenario": "Rama sin reglas de protección configuradas en SCM (evidencia nula o rama libre).",
        "repository": "Medalcode/securecode-ground-truth",
        "branch": "branch-case-5-unprotected",
        "expected_status": "UNKNOWN",
        "evidence_preview": {
            "required_review_approvals": None,
            "dismiss_stale_reviews": None
        },
        "rationale": "Estado no evaluable (NULL): no existen reglas configuradas sobre la rama en GitHub."
    },
    {
        "case_id": "GT-GH001-06",
        "control_id": "GH-001",
        "title": "UNKNOWN - Evidencia Incompleta o Indeterminada",
        "scenario": "Respuesta parcial de API o verificación incompleta por permisos insuficientes.",
        "repository": "Medalcode/securecode-ground-truth",
        "branch": "branch-case-6-status-checks-only",
        "expected_status": "UNKNOWN",
        "evidence_preview": {
            "required_review_approvals": None,
            "dismiss_stale_reviews": None
        },
        "rationale": "Estado indeterminado: la evidencia requerida para la regla no pudo ser reconstruida de forma fidedigna."
    },
    {
        "case_id": "GT-GH002-01",
        "control_id": "GH-002",
        "title": "PASS - Rama Principal Protegida",
        "scenario": "Rama 'main' tiene protección explícitamente habilitada contra sobreescritura.",
        "repository": "Medalcode/securecode-ground-truth",
        "branch": "main",
        "expected_status": "PASS",
        "evidence_preview": {
            "default_branch": "main",
            "protection_enabled": True
        },
        "rationale": "Satisface el control GH-002: protection_enabled == True sobre la rama principal."
    },
    {
        "case_id": "GT-GH002-02",
        "control_id": "GH-002",
        "title": "FAIL - Rama Principal Sin Protección",
        "scenario": "Rama 'main' configurada con protección explícitamente deshabilitada (vulnerable a force-push).",
        "repository": "Medalcode/securecode-ground-truth",
        "branch": "main",
        "expected_status": "FAIL",
        "evidence_preview": {
            "default_branch": "main",
            "protection_enabled": False
        },
        "rationale": "Infracción crítica: protection_enabled == False permite force push directo a producción."
    },
    {
        "case_id": "GT-GH002-03",
        "control_id": "GH-002",
        "title": "UNKNOWN - Estado de Protección No Provisto",
        "scenario": "No es posible determinar el estado de protección de la rama (metadata ausente).",
        "repository": "Medalcode/securecode-ground-truth",
        "branch": "main",
        "expected_status": "UNKNOWN",
        "evidence_preview": {
            "default_branch": "main",
            "protection_enabled": None
        },
        "rationale": "Estado triestado UNKNOWN: protection_enabled == None (evidencia indeterminada)."
    }
]

def list_ground_truth_cases(control_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns canonical Ground Truth test cases filtered by control if specified."""
    if not control_filter or control_filter == "Todos":
        return GROUND_TRUTH_CASES
    return [c for c in GROUND_TRUTH_CASES if c["control_id"] == control_filter]

def run_single_test_case(case_id: str, override_evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes a single Ground Truth test case through the deterministic evaluation engine,
    calculates precise execution time (ms), canonical SHA-256 hash, and verifies
    concordance with the expected Oracle verdict.
    """
    case = next((c for c in GROUND_TRUTH_CASES if c["case_id"] == case_id), None)
    if not case:
        raise ValueError(f"Ground Truth case '{case_id}' not found")

    control_id = case["control_id"]
    evidence_data = dict(case["evidence_preview"])
    if override_evidence:
        evidence_data.update(override_evidence)

    # High precision timer start
    start_time = time.perf_counter()

    if control_id == "GH-001":
        req_approvals = evidence_data.get("required_review_approvals")
        dismiss_stale = evidence_data.get("dismiss_stale_reviews")
        
        # Build domain model evidence
        evidence_obj = GH001Evidence(
            required_review_approvals=req_approvals,
            dismiss_stale_reviews=dismiss_stale
        )
        status_enum = evaluate_gh001(evidence_obj)
        canonical_hash = evidence_obj.canonical_hash()
        rule_name = "GH-001-RULE (Revisión por Pares)"
        rule_ver = 1
    elif control_id == "GH-002":
        default_branch = evidence_data.get("default_branch", "main")
        protection_enabled = evidence_data.get("protection_enabled")

        evidence_obj = GH002Evidence(
            default_branch=default_branch,
            protection_enabled=protection_enabled
        )
        status_enum = evaluate_gh002(evidence_obj)
        canonical_hash = evidence_obj.canonical_hash()
        rule_name = "GH-002-RULE (Protección de Rama Principal)"
        rule_ver = 1
    else:
        raise ValueError(f"Unsupported control '{control_id}'")

    # High precision timer stop
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

    actual_status = status_enum.name
    expected_status = case["expected_status"]
    matched = (actual_status == expected_status)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if matched:
        explanation = f"Concordancia exitosa (100%): El motor determinista resolvió '{actual_status}', coincidiendo exactamente con el oráculo empírico '{expected_status}'."
    else:
        explanation = f"Discrepancia detectada: El motor resolvió '{actual_status}', mientras que el oráculo esperaba '{expected_status}'."

    return {
        "case_id": case_id,
        "control_id": control_id,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "matched": matched,
        "execution_time_ms": max(elapsed_ms, 0.05),
        "evidence": evidence_data,
        "integrity_hash": canonical_hash,
        "rule_applied": rule_name,
        "rule_version": rule_ver,
        "evaluated_at": now_utc,
        "explanation": explanation,
        "oracle_verdict_rationale": case["rationale"]
    }
