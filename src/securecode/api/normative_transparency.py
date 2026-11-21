"""Reusable public content for normative transparency."""

from __future__ import annotations

import json
from html import escape

from securecode.engine.evaluator import get_rules_directory
from securecode.models.rules import AndCondition, Condition, RuleDefinition

SCOPE_WARNING = (
    "SecureCode no certifica cumplimiento NIST o ISO, no constituye una auditoría "
    "integral de ciberseguridad y no garantiza ausencia de vulnerabilidades."
)

CONTROL_METADATA: dict[str, dict[str, object]] = {
    "GH-001": {
        "name": "Revisiones aprobadas y descarte de aprobaciones obsoletas",
        "objective": "Comprobar que los cambios revisados cuentan con aprobaciones suficientes y que una aprobación deja de ser válida cuando la rama recibe nuevos cambios.",
        "rule_plain": "El número de aprobaciones requeridas debe ser mayor o igual que 2 y las reseñas obsoletas deben descartarse automáticamente.",
        "nist": "CM-3 Configuration Change Control; CM-3(1) y CM-5(4) como fortalecimientos de apoyo. Correspondencia parcial: el umbral de dos aprobaciones es política de SecureCode.",
        "evidence": "required_review_approvals y dismiss_stale_reviews, obtenidos de la configuración de protección de la rama en GitHub.",
        "pass": "Ambas condiciones se cumplen: aprobaciones requeridas ≥ 2 y descarte de reseñas obsoletas activo.",
        "fail": "Al menos una condición determinante se incumple con evidencia suficiente, por ejemplo aprobaciones requeridas < 2 o descarte desactivado.",
        "unknown": "Falta evidencia, algún campo relevante es nulo o el tipo del dato no permite aplicar la regla.",
        "limitations": "No evalúa la calidad de la revisión, la identidad del aprobador, el análisis de impacto de seguridad o privacidad ni la coincidencia entre revisión y código fusionado.",
    },
    "GH-002": {
        "name": "Protección de la rama principal",
        "objective": "Verificar que la rama por defecto del repositorio tenga protección activa y no pueda recibir cambios directos sin control.",
        "rule_plain": "La protección de la rama principal debe estar activa.",
        "nist": "CM-5 Access Restrictions for Change y CM-5(1) Automated Access Enforcement and Audit Records. Correspondencia parcial: no se validan políticas organizacionales ni registros de auditoría.",
        "evidence": "default_branch como localizador y protection_enabled como estado observable de la protección de la rama por defecto.",
        "pass": "La protección de la rama por defecto está activa.",
        "fail": "La rama existe pero su protección no está configurada.",
        "unknown": "No puede resolverse el repositorio o la rama, o la respuesta de GitHub no permite decidir.",
        "limitations": "No evalúa permisos efectivos, CODEOWNERS, verificaciones obligatorias, restricciones de push ni generación de registros de auditoría.",
    },
    "GH-003": {
        "name": "Exigencia de commits firmados",
        "objective": "Comprobar que la rama evaluada exige firmas criptográficas en los commits antes de aceptarlos.",
        "rule_plain": "La rama evaluada debe exigir commits firmados.",
        "nist": "CM-14 Signed Components como referencia principal; SI-7, SI-7(1) y SI-7(6) como apoyo indirecto a la integridad. Correspondencia parcial: no se trata de una equivalencia con SI-7 ni con el retirado CM-5(3).",
        "evidence": "branch como localizador y required_signatures_enabled como estado observable del requisito de firmas en la rama.",
        "pass": "La rama evaluada exige commits firmados.",
        "fail": "La rama existe pero no exige commits firmados.",
        "unknown": "No puede resolverse la rama o la respuesta de GitHub no permite decidir.",
        "limitations": "No valida la firma de cada commit, certificados, cadena de confianza, política organizacional de firma ni integridad de componentes instalados.",
    },
}

NIST_CONTROL_MAPPINGS: dict[str, tuple[dict[str, str], ...]] = {
    "GH-001": (
        {"id": "CM-3", "relationship": "objetivo principal"},
        {"id": "CM-3(1)", "relationship": "fortalecimiento de apoyo"},
        {"id": "CM-5(4)", "relationship": "fortalecimiento de apoyo"},
    ),
    "GH-002": (
        {"id": "CM-5", "relationship": "objetivo principal"},
        {"id": "CM-5(1)", "relationship": "fortalecimiento de apoyo parcial"},
    ),
    "GH-003": (
        {"id": "CM-14", "relationship": "objetivo principal"},
        {"id": "SI-7", "relationship": "apoyo indirecto a la integridad"},
        {"id": "SI-7(1)", "relationship": "apoyo indirecto a la integridad"},
        {"id": "SI-7(6)", "relationship": "apoyo indirecto a la integridad"},
    ),
}

SCOPE_INCLUDED = (
    "Evaluación determinista de configuraciones técnicas observables de repositorios GitHub.",
    "Reglas declarativas versionadas, consultables antes de ejecutar una evaluación.",
    "Evidencia normalizada, huella SHA-256 y resultado PASS, FAIL o UNKNOWN.",
    "Trazabilidad documental parcial con objetivos seleccionados de NIST SP 800-53 Rev. 5.",
)

SCOPE_EXCLUDED = (
    "Certificación NIST, ISO o de cualquier otro marco.",
    "Auditoría integral de ciberseguridad ni garantía de ausencia de vulnerabilidades.",
    "Evaluación de procesos organizacionales, personas, políticas completas o entrevistas.",
    "Cambios en configuraciones de GitHub: SecureCode solo observa y reporta.",
)


def load_canonical_rules() -> dict[str, RuleDefinition]:
    rules: dict[str, RuleDefinition] = {}
    rules_dir = get_rules_directory()
    if not rules_dir.exists():
        return rules
    for rule_path in sorted(rules_dir.glob("GH-*.json")):
        try:
            definition = RuleDefinition(**json.loads(rule_path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
        if definition.control_id in CONTROL_METADATA and definition.active:
            rules[definition.control_id] = definition
    return rules


def format_condition(condition: Condition | AndCondition) -> str:
    if isinstance(condition, AndCondition):
        return " AND ".join(format_condition(child) for child in condition.conditions)
    return f"{condition.field} {condition.operator} {json.dumps(condition.value)}"


def _detail(label: str, value: str, *, code: bool = False) -> str:
    rendered = f"<code>{escape(value)}</code>" if code else escape(value)
    return f'<div class="control-row"><dt>{escape(label)}</dt><dd>{rendered}</dd></div>'


def render_framework_section() -> str:
    return """
<section class="normative-section" id="marco" aria-labelledby="marco-title">
  <div class="section-heading"><p class="eyebrow">TRANSPARENCIA NORMATIVA</p><h2 id="marco-title">Nuestro marco de referencia</h2><p>NIST SP 800-53 Rev. 5 es el marco de referencia principal para objetivos seleccionados de seguridad. NIST SP 800-53A Rev. 5 orienta metodológicamente la evaluación mediante evidencias técnicas. Sobre esa base, SecureCode implementa reglas específicas de GitHub. Estas reglas no representan una certificación ni una evaluación integral de NIST.</p></div>
  <div class="framework-grid">
    <article><span class="pill">Marco principal</span><h3>NIST SP 800-53 Rev. 5</h3><p>Selecciona objetivos de control relevantes para la seguridad de repositorios. SecureCode no cubre el catálogo completo. No sustituye una evaluación organizacional.</p></article>
    <article><span class="pill">Metodología</span><h3>NIST SP 800-53A Rev. 5</h3><p>Apoya la forma de describir evidencia, determinaciones y limitaciones. No emite hallazgos formales ni conclusiones de auditoría.</p></article>
    <article><span class="pill">Implementación</span><h3>Reglas de GitHub</h3><p>Reglas técnicas y versionadas que consultan configuración observable. Cada resultado indica qué condición se evaluó y con qué evidencia.</p></article>
  </div>
</section>
"""


def render_methodology_section() -> str:
    return """
<section class="normative-section methodology-section" id="metodologia" aria-labelledby="metodologia-title">
  <div class="section-heading"><p class="eyebrow">CÓMO SE EVALÚA</p><h2 id="metodologia-title">Metodología de evaluación</h2><p>La evaluación es reproducible, consultable y está separada de la autenticación y de la contratación.</p></div>
  <ol class="method-list">
    <li><strong>Regla canónica:</strong> cada control tiene una condición exacta y una versión publicada antes de ejecutarse.</li>
    <li><strong>Evidencia observable:</strong> el adaptador consulta únicamente configuración técnica de GitHub y produce campos normalizados.</li>
    <li><strong>Decisión determinista:</strong> el motor aplica la regla sin azar, modelos externos ni interpretación subjetiva.</li>
    <li><strong>Resultado triestado:</strong> PASS, FAIL y UNKNOWN conservan su significado distinto y se registran con la versión de la regla.</li>
  </ol>
</section>
"""


def render_controls_section() -> str:
    rules = load_canonical_rules()
    cards: list[str] = []
    for control_id in sorted(CONTROL_METADATA):
        definition = rules.get(control_id)
        if definition is None:
            continue
        meta = CONTROL_METADATA[control_id]
        condition = format_condition(definition.condition)
        rows = "".join(
            (
                _detail("Identificador de regla", str(definition.rule_id), code=True),
                _detail("Regla técnica exacta", condition, code=True),
                _detail("Versión de la regla", str(definition.version)),
                _detail("Objetivo de seguridad", str(meta["objective"])),
                _detail("Lectura en lenguaje claro", str(meta["rule_plain"])),
                _detail("Referencia normativa parcial", str(meta["nist"])),
                _detail("Evidencia utilizada", str(meta["evidence"])),
                _detail("Limitaciones", str(meta["limitations"])),
            )
        )
        criteria = "".join(
            (
                f'<li><strong>PASS:</strong> {escape(str(meta["pass"]))}</li>',
                f'<li><strong>FAIL:</strong> {escape(str(meta["fail"]))}</li>',
                f'<li><strong>UNKNOWN:</strong> {escape(str(meta["unknown"]))}</li>',
            )
        )
        cards.append(
            f'<article class="control-card" id="control-{control_id.lower()}" aria-labelledby="{control_id.lower()}-title">'
            f'<div class="control-head"><span class="control-id">{escape(control_id)}</span><span class="pill">Regla v{definition.version}</span></div>'
            f'<h3 id="{control_id.lower()}-title">{escape(str(meta["name"]))}</h3>'
            f'<dl class="control-details">{rows}</dl>'
            f'<h4>Criterios del resultado</h4><ul class="control-criteria">{criteria}</ul>'
            "</article>"
        )
    controls = "".join(cards)
    return f"""
<section class="normative-section" id="controles" aria-labelledby="controles-title">
  <div class="section-heading"><p class="eyebrow">CONTROLES IMPLEMENTADOS</p><h2 id="controles-title">Controles de seguridad</h2><p>Consulta qué evalúa SecureCode, con qué regla exacta y dentro de qué límite. Las condiciones mostradas se generan desde el catálogo canónico de reglas.</p></div>
  <div class="control-grid">{controls}</div>
</section>
"""


STATUS_MEANINGS = (
    (
        "PASS",
        "La evidencia disponible demuestra que se cumplen las condiciones de la regla evaluada.",
        "No significa que un repositorio esté completamente seguro.",
    ),
    (
        "FAIL",
        "La evidencia disponible demuestra el incumplimiento de al menos una condición determinante de la regla.",
        "Describe el incumplimiento observable de esa regla, no de todo el repositorio.",
    ),
    (
        "UNKNOWN",
        "La evidencia disponible no permite establecer el resultado.",
        "No equivale a FAIL: indica información insuficiente o no interpretable.",
    ),
)


def render_results_section() -> str:
    cards = "".join(
        f'<article class="status-card status-{status.lower()}"><h3>{status}</h3><p>{escape(meaning)}</p><p class="muted">{escape(note)}</p></article>'
        for status, meaning, note in STATUS_MEANINGS
    )
    return f"""
<section class="normative-section" id="resultados" aria-labelledby="resultados-title">
  <div class="section-heading"><p class="eyebrow">LECTURA DE DICTÁMENES</p><h2 id="resultados-title">Cómo interpretamos los resultados</h2></div>
  <div class="status-grid">{cards}</div>
  <p class="scope-warning compact-warning">PASS no significa que un repositorio esté completamente seguro. UNKNOWN no equivale a FAIL.</p>
</section>
"""


def render_scope_section() -> str:
    included = "".join(f"<li>{escape(item)}</li>" for item in SCOPE_INCLUDED)
    excluded = "".join(f"<li>{escape(item)}</li>" for item in SCOPE_EXCLUDED)
    return f"""
<section class="normative-section scope-section" id="alcance" aria-labelledby="alcance-title">
  <div class="section-heading"><p class="eyebrow">LÍMITES DEL SERVICIO</p><h2 id="alcance-title">Qué hace SecureCode y qué no hace</h2><p class="scope-warning">{escape(SCOPE_WARNING)}</p></div>
  <div class="scope-grid">
    <article><h3>Incluido</h3><ul class="scope-list included">{included}</ul></article>
    <article><h3>Excluido</h3><ul class="scope-list excluded">{excluded}</ul></article>
  </div>
  <p>Consulta esta información antes de cualquier acción de contratación o suscripción. <a class="text-link" href="/legal/contratacion">Ver condiciones de contratación <span aria-hidden="true">→</span></a></p>
</section>
"""


def render_home_normative_sections() -> str:
    return (
        render_framework_section()
        + render_methodology_section()
        + render_controls_section()
        + render_results_section()
        + render_scope_section()
    )
