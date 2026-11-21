# Fichas técnicas de controles GH

Este documento complementa la matriz de trazabilidad con una ficha uniforme por control. Cada ficha describe únicamente comportamiento verificado en el código canónico y su relación parcial con NIST SP 800-53 Rev. 5. No sustituye a los procedimientos de evaluación de SP 800-53A ni constituye una certificación.

## Convenciones comunes

- La regla canónica se carga desde `src/securecode/rules/<CONTROL>.json` mediante `get_rule_definition()`.
- `get_rules_directory()` permite sustituir el directorio con `SECURECODE_RULES_DIR`; la documentación se verifica contra el directorio empaquetado por defecto.
- `RuleDefinition.version` es `1` para GH-001, GH-002 y GH-003. El número de versión forma parte de la trazabilidad de la evaluación.
- `RuleDefinition.allowlisted_fields` restringe qué campos pueden aparecer en la condición; un campo puede estar permitido sin ser evaluado, como `default_branch` en GH-002 o `branch` en GH-003.
- El evaluador es determinista: la misma evidencia produce el mismo `EvaluationStatus`.
- `FAIL` significa incumplimiento observable; `UNKNOWN` significa evidencia insuficiente o no interpretable. No son intercambiables.
- En reglas `AND`, un `FAIL` prevalece sobre un `UNKNOWN`; si no hay `FAIL` pero hay `UNKNOWN`, el resultado es `UNKNOWN`; solo todas las condiciones en `PASS` producen `PASS`.

## Ficha GH-001

| Campo | Valor |
|---|---|
| Control | `GH-001` |
| Nombre | Revisión aprobada y descarte de reseñas obsoletas en rama protegida |
| Rule ID | `GH-001-RULE` |
| Versión de regla | `1` |
| Activa | `true` |
| Archivo canónico | `src/securecode/rules/GH-001.json` |
| Evaluador | `evaluate_gh001` |
| Modelo de evidencia | `GH001Evidence` |
| Condición canónica | `required_review_approvals GTE 2 AND dismiss_stale_reviews EQ true` |
| NIST relacionado (parcial) | `CM-3`, `CM-3(1)`, `CM-5(4)` |

### Evidencia requerida

| Campo | Tipo | Origen | Uso en la regla |
|---|---|---|---|
| `required_review_approvals` | `int | None` | `required_pull_request_reviews.required_approving_review_count` de GitHub | Evaluado con `GTE 2` |
| `dismiss_stale_reviews` | `bool | None` | `required_pull_request_reviews.dismiss_stale_reviews` de GitHub | Evaluado con `EQ true` |

El adaptador consulta repositorio, rama y protección de rama. Si el repositorio o la rama no son accesibles, devuelve campos `None`. Si no existe protección o no hay configuración de revisiones obligatorias, devuelve `required_review_approvals=0` y `dismiss_stale_reviews=false`, lo cual produce `FAIL`.

### Semántica de resultado

| Estado | Condición |
|---|---|
| `PASS` | `required_review_approvals >= 2` y `dismiss_stale_reviews == true`. |
| `FAIL` | `required_review_approvals < 2` o `dismiss_stale_reviews == false`, con evidencia suficiente. |
| `UNKNOWN` | Falta evidencia, algún campo relevante es `None`, hay incompatibilidad de tipos o la evidencia global es `None`; `FAIL` prevalece cuando existe una violación conocida, aunque otro campo sea `UNKNOWN`. |

### Justificación normativa parcial

`CM-3 Configuration Change Control` exige que los cambios controlados sean revisados y aprobados o desaprobados. `CM-3(1)` añade mecanismos automatizados que documentan, notifican y prohíben cambios hasta recibir aprobaciones designadas. `CM-5(4) Dual Authorization` exige autorización dual para components o información definidos por la organización. SecureCode verifica una configuración automática de GitHub, no el proceso completo de cambio ni la identidad de quien aprueba. El valor `2` es una política interna de SecureCode.

### Exclusiones específicas

No se evalúan análisis de impacto de seguridad o privacidad, contenido de la revisión, identidad o autoridad de los aprobadores, coincidencia entre revisiones y commits fusionados, ni cumplimiento de `CM-3c`, `CM-3d`, `CM-3e`, `CM-3f` o `CM-3g`.

## Ficha GH-002

| Campo | Valor |
|---|---|
| Control | `GH-002` |
| Nombre | Protección activa de la rama por defecto |
| Rule ID | `GH-002-RULE` |
| Versión de regla | `1` |
| Activa | `true` |
| Archivo canónico | `src/securecode/rules/GH-002.json` |
| Evaluador | `evaluate_gh002` |
| Modelo de evidencia | `GH002Evidence` |
| Condición canónica | `protection_enabled EQ true` |
| NIST relacionado (parcial) | `CM-5`, `CM-5(1)` |

### Evidencia requerida

| Campo | Tipo | Origen | Uso en la regla |
|---|---|---|---|
| `default_branch` | `str` | `default_branch` de `GET /repos/{owner}/{repo}` | Localizador; permitido pero no evaluado |
| `protection_enabled` | `bool | None` | Estado HTTP del endpoint de protección de la rama por defecto | Evaluado con `EQ true` |

El adaptador resuelve primero la rama por defecto y comprueba que exista. Después consulta su protección: `200` implica `true`, `404` implica `false` y cualquier otra respuesta no concluyente implica `None`.

### Semántica de resultado

| Estado | Condición |
|---|---|
| `PASS` | `protection_enabled == true`. |
| `FAIL` | `protection_enabled == false`. |
| `UNKNOWN` | `protection_enabled` es `None` o la evidencia global es `None`. |

### Justificación normativa parcial

`CM-5 Access Restrictions for Change` incluye definir, aprobar y aplicar restricciones lógicas a los cambios. La protección de la rama por defecto es un mecanismo automatizado que restringe cambios directos; por eso la relación con `CM-5` y `CM-5(1) Automated Access Enforcement and Audit Records` es parcial y técnica. SecureCode no determina si las restricciones están aprobadas por la organización ni si se generan registros de auditoría.

### Exclusiones específicas

No se evalúan permisos efectivos de escritura, `CODEOWNERS`, reglas de verificación de estado, restricciones de push/fuerza, auditoría de enforcement, ni la totalidad de los objetivos `CM-05[01]` a `CM-05[06]`.

## Ficha GH-003

| Campo | Valor |
|---|---|
| Control | `GH-003` |
| Nombre | Exigencia de commits firmados en la rama evaluada |
| Rule ID | `GH-003-RULE` |
| Versión de regla | `1` |
| Activa | `true` |
| Archivo canónico | `src/securecode/rules/GH-003.json` |
| Evaluador | `evaluate_gh003` |
| Modelo de evidencia | `GH003Evidence` |
| Condición canónica | `required_signatures_enabled EQ true` |
| NIST relacionado (parcial) | `CM-14`, `SI-7`, `SI-7(1)`, `SI-7(6)` |

### Evidencia requerida

| Campo | Tipo | Origen | Uso en la regla |
|---|---|---|---|
| `branch` | `str` | Parámetro de la evaluación | Localizador; permitido pero no evaluado |
| `required_signatures_enabled` | `bool | None` | Estado HTTP de `protection/required_signatures` | Evaluado con `EQ true` |

El adaptador comprueba que la rama exista y consulta el endpoint de firmas requeridas: `200` implica `true`, `404` implica `false` y cualquier otra respuesta no concluyente implica `None`.

### Semántica de resultado

| Estado | Condición |
|---|---|
| `PASS` | `required_signatures_enabled == true`. |
| `FAIL` | `required_signatures_enabled == false`. |
| `UNKNOWN` | `required_signatures_enabled` es `None` o la evidencia global es `None`. |

### Justificación normativa parcial

La relación principal es con `CM-14 Signed Components`. En SP 800-53 Rev. 5, `CM-05(03) Signed Components` fue retirado y trasladado a `CM-14`; por eso no debe documentarse GH-003 como equivalente a `CM-5(3)`. `CM-14[01]` exige verificar que los componentes de software estén firmados digitalmente con un certificado reconocido y aprobado. SecureCode solo observa si GitHub exige firmas en una rama; no valida el certificado ni la cadena de confianza.

`SI-7 Software, Firmware, and Information Integrity` se registra como apoyo indirecto a la integridad, con `SI-7(1) Integrity Checks` y `SI-7(6) Cryptographic Protection`. `SI-07(06)[01]` se refiere a mecanismos criptográficos para detectar cambios no autorizados en software, lo cual no equivale a exigir commits firmados. La correspondencia con SI-7 es, por tanto, parcial y de apoyo.

### Exclusiones específicas

No se verifica la firma de cada commit, la validez del certificado, la política organizacional de firma, la instalación de software o firmware, la integridad de artefactos desplegados ni los objetivos completos de CM-14 o SI-7. No existe `docs/specs/GH-003.md`; esta ficha documenta la regla vigente sin crear una spec ejecutable paralela.

## Consistencia verificable

- Los tres Rule ID, versiones, condiciones y modelos de evidencia de estas fichas se comprueban contra los JSON canónicos mediante `tests/unit/test_normative_documentation.py`.
- Las fichas no introducen nuevos umbrales ni cambian la semántica de `PASS`, `FAIL` o `UNKNOWN`.
- Cualquier cambio de regla debe actualizar primero el JSON canónico y después este documento y la matriz.
