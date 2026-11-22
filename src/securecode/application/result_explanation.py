from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from securecode.api.normative_transparency import (
    CONTROL_METADATA,
    NIST_CONTROL_MAPPINGS,
    SCOPE_WARNING,
    STATUS_MEANINGS,
    format_condition,
)
from securecode.engine.evaluator import get_rule_definition
from securecode.engine.executor import evaluate_condition, evaluate_rule
from securecode.engine.types import EvaluationStatus
from securecode.models.gh001 import GH001Evidence
from securecode.models.gh002 import GH002Evidence
from securecode.models.gh003 import GH003Evidence
from securecode.models.rules import AndCondition, Condition, RuleDefinition

_EVIDENCE_MODELS = {
    "GH-001": (GH001Evidence, "GH-001.json"),
    "GH-002": (GH002Evidence, "GH-002.json"),
    "GH-003": (GH003Evidence, "GH-003.json"),
}

_FIELD_LABELS = {
    "required_review_approvals": "Aprobaciones requeridas",
    "dismiss_stale_reviews": "Descarte de reseñas obsoletas",
    "default_branch": "Rama predeterminada",
    "protection_enabled": "Protección de rama activa",
    "branch": "Rama evaluada",
    "required_signatures_enabled": "Commits firmados exigidos",
}

_FIELD_REMEDIATION = {
    "required_review_approvals": "Configura al menos dos aprobaciones requeridas en la protección de la rama.",
    "dismiss_stale_reviews": "Activa el descarte automático de aprobaciones obsoletas cuando se incorporan nuevos cambios.",
    "protection_enabled": "Activa la protección de la rama predeterminada en la configuración de GitHub.",
    "required_signatures_enabled": "Activa la opción que exige commits firmados para la rama evaluada.",
}


def _status(value: EvaluationStatus | str) -> EvaluationStatus:
    if isinstance(value, EvaluationStatus):
        return value
    try:
        return EvaluationStatus(str(value).upper())
    except ValueError:
        return EvaluationStatus.UNKNOWN


def _status_meaning(status: EvaluationStatus) -> tuple[str, str]:
    for code, meaning, note in STATUS_MEANINGS:
        if code == status.name:
            return meaning, note
    return "La evidencia disponible no permite establecer el resultado.", "UNKNOWN no equivale a FAIL."


def _conditions(rule: RuleDefinition) -> list[Condition]:
    if isinstance(rule.condition, AndCondition):
        return list(rule.condition.conditions)
    return [rule.condition]


def _display_value(value: Any) -> str:
    if value is None:
        return "No disponible"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _expected_value(condition: Condition) -> str:
    return f"{condition.operator} {json.dumps(condition.value, ensure_ascii=False)}"


def _condition_reason(condition: Condition, observed: Any, result: EvaluationStatus) -> str:
    expected = _expected_value(condition)
    if result == EvaluationStatus.PASS:
        return f"El valor observado ({_display_value(observed)}) cumple la condición {expected}."
    if result == EvaluationStatus.FAIL:
        return f"El valor observado ({_display_value(observed)}) incumple la condición {expected}."
    return f"No es posible aplicar la condición {expected} porque el valor observado es nulo o no interpretable."


def _recommendations(status: EvaluationStatus, results: list[dict[str, Any]]) -> list[str]:
    if status == EvaluationStatus.PASS:
        return [
            "Conserva la configuración observada y vuelve a evaluar después de cualquier cambio relevante en la rama."
        ]

    failed = {item["field"] for item in results if item["status"] == EvaluationStatus.FAIL.name}
    missing = {item["field"] for item in results if item["status"] == EvaluationStatus.UNKNOWN.name}
    recommendations: list[str] = []
    for field in sorted(failed):
        remediation = _FIELD_REMEDIATION.get(field)
        if remediation:
            recommendations.append(remediation)
    if status == EvaluationStatus.UNKNOWN:
        recommendations.append(
            "Verifica que el repositorio y la rama existan y que el token de GitHub tenga permisos de lectura suficientes."
        )
        for field in sorted(missing):
            label = _FIELD_LABELS.get(field, field)
            recommendations.append(f"Confirma que el campo {label} pueda observarse desde la API de GitHub.")
    if not recommendations:
        recommendations.append("Revisa la configuración de la regla y vuelve a ejecutar la evaluación.")
    recommendations.append("SecureCode solo observa la configuración: aplica cualquier cambio directamente en GitHub.")
    return recommendations


def _load_rule(control_id: str, warnings: list[str]) -> RuleDefinition | None:
    model_and_file = _EVIDENCE_MODELS.get(control_id)
    if model_and_file is None:
        warnings.append("El control almacenado no tiene una definición de evidencia reconocida.")
        return None
    try:
        return get_rule_definition(model_and_file[1])
    except (OSError, ValueError) as error:
        warnings.append(f"No se pudo cargar la regla canónica: {error}.")
        return None


def build_result_explanation(
    *,
    control_id: str,
    rule_id: str | None,
    rule_version: int | None,
    status: EvaluationStatus | str,
    evidence: GH001Evidence | GH002Evidence | GH003Evidence,
    evidence_hash: str,
) -> dict[str, Any]:
    stored_status = _status(status)
    metadata = CONTROL_METADATA.get(control_id, {})
    meaning, note = _status_meaning(stored_status)
    warnings: list[str] = []

    rule = _load_rule(control_id, warnings)
    if rule is not None and rule.control_id != control_id:
        warnings.append("La regla canónica cargada no corresponde al control almacenado.")

    recomputed_hash = evidence.canonical_hash()
    integrity_valid = recomputed_hash == evidence_hash
    if not integrity_valid:
        warnings.append("La huella reconstruida no coincide con la huella almacenada; se conserva el dictamen histórico.")

    condition_results: list[dict[str, Any]] = []
    computed_status: EvaluationStatus | None = None
    if rule is not None:
        computed_status = evaluate_rule(rule, evidence)
        for condition in _conditions(rule):
            observed = getattr(evidence, condition.field, None)
            condition_status = evaluate_condition(condition, evidence)
            condition_results.append(
                {
                    "field": condition.field,
                    "label": _FIELD_LABELS.get(condition.field, condition.field),
                    "operator": condition.operator,
                    "expected": condition.value,
                    "expected_display": _expected_value(condition),
                    "observed": observed,
                    "observed_display": _display_value(observed),
                    "status": condition_status.name,
                    "explanation": _condition_reason(condition, observed, condition_status),
                }
            )
        if computed_status != stored_status:
            warnings.append(
                f"La evidencia reconstruida produce {computed_status.name}, pero el dictamen almacenado es {stored_status.name}."
            )
        if rule_id and rule.rule_id != rule_id:
            warnings.append("El identificador de regla almacenado difiere del catálogo canónico actual.")
        if rule_version is not None and rule.version != rule_version:
            warnings.append("La versión de regla almacenada difiere del catálogo canónico actual.")

    if stored_status == EvaluationStatus.PASS:
        reason = "Todas las condiciones evaluadas se cumplen con la evidencia disponible."
    elif stored_status == EvaluationStatus.FAIL:
        failed_labels = [
            item["label"] for item in condition_results if item["status"] == EvaluationStatus.FAIL.name
        ]
        reason = str(metadata.get("fail", "Al menos una condición determinante se incumple."))
        if failed_labels:
            reason = f"{reason} Condiciones incumplidas: {', '.join(failed_labels)}."
    else:
        reason = str(
            metadata.get(
                "unknown",
                "La evidencia disponible no permite establecer el resultado; UNKNOWN no equivale a FAIL.",
            )
        )

    if computed_status is not None and computed_status != stored_status:
        reason = (
            f"ADVERTENCIA: el dictamen histórico es {stored_status.name}, pero la evidencia reconstruida produce "
            f"{computed_status.name}. {reason}"
        )

    recommendations = _recommendations(stored_status, condition_results)
    if computed_status is not None and computed_status != stored_status:
        recommendations.insert(
            0,
            "No modificar el dictamen histórico; investiga la inconsistencia entre la evidencia reconstruida y el resultado almacenado antes de nuevas evaluaciones.",
        )

    return {
        "summary": {
            "status": stored_status.name,
            "reason": reason,
            "meaning": meaning,
            "note": note,
            "scope_warning": SCOPE_WARNING,
        },
        "rule": {
            "id": rule_id or (rule.rule_id if rule else None),
            "version": rule_version if rule_version is not None else (rule.version if rule else None),
            "expression": format_condition(rule.condition) if rule else str(metadata.get("rule_plain", "")),
            "allowlisted_fields": list(rule.allowlisted_fields) if rule else [],
            "loaded_from_catalog": rule is not None,
        },
        "conditions": condition_results,
        "evidence": {
            "fields": asdict(evidence),
            "stored_hash": evidence_hash,
            "recomputed_hash": recomputed_hash,
            "integrity_valid": integrity_valid,
        },
        "normative_traceability": {
            "framework": "NIST SP 800-53 Rev. 5",
            "methodology": "NIST SP 800-53A Rev. 5",
            "objective": str(metadata.get("objective", "")),
            "controls": [dict(control) for control in NIST_CONTROL_MAPPINGS.get(control_id, ())],
            "correspondence": "parcial",
            "limitations": str(metadata.get("limitations", "")),
            "disclaimer": SCOPE_WARNING,
        },
        "recommendations": recommendations,
        "reconstruction": {
            "computed_status": computed_status.name if computed_status else None,
            "consistent_with_stored_status": computed_status == stored_status if computed_status else False,
            "warnings": warnings,
        },
    }
