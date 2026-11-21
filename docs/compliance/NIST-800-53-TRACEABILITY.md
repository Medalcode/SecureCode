# Matriz de trazabilidad normativa NIST SP 800-53 Rev. 5

## Propósito

Este documento establece la trazabilidad entre los controles GH-001, GH-002 y GH-003 de SecureCode y los controles de NIST SP 800-53 Rev. 5 / SP 800-53A Rev. 5. La correspondencia es **parcial y documental**: SecureCode evalúa configuraciones técnicas observables de GitHub; no certifica el cumplimiento de un sistema, organización o proceso.

La fuente canónica de las reglas ejecutadas en runtime es `src/securecode/rules/`. El directorio `rules/` en la raíz contiene copias JSON-equivalentes, pero no es la fuente que carga el motor salvo que se configure `SECURECODE_RULES_DIR`. Este documento no crea un catálogo paralelo: cada afirmación tecnológica se deriva de los archivos canónicos y se verifica mediante pruebas automáticas.

## Fuentes normativas

| Fuente | Uso en este documento |
|---|---|
| NIST SP 800-53 Rev. 5, `https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf` | Definición de controles y fortalecimientos. |
| NIST SP 800-53 Rev. 5 derivado OSCAL, `https://csrc.nist.gov/CSRC/media/Projects/risk-management/800-53%20Downloads/800-53r5/SP_800-53_v5_1-derived-OSCAL.pdf` | Verificación legible por máquina de identificadores y títulos. |
| NIST SP 800-53A Rev. 5, `https://csrc.nist.gov/pubs/sp/800/53/a/r5/final` | Metodología de evaluación: objectives, determination statements, methods y findings. |
| Procedimientos de evaluación SP 800-53A Rev. 5, `https://csrc.nist.gov/files/pubs/sp/800/53/a/r5/final/docs/sp800-53ar5-assessment-procedures.txt` | Texto exacto de determination statements y potential assessment methods para CM-3, CM-5, CM-14 y SI-7. |

## Convenciones de correspondencia

- **Correspondencia parcial:** el control de SecureCode cubre una parte del objetivo NIST, no todo el control ni todos sus fortalecimientos.
- **Fortalecimiento:** un control de SecureCode puede apoyar un control base NIST y, además, un fortalecimiento; esto no convierte al fortalecimiento en obligatorio por parte de SecureCode.
- **Umbral interno:** el número `2` de aprobaciones de GH-001 es una decisión de política de SecureCode; NIST no prescribe ese número exacto.
- **No certificación:** las tablas y fichas son evidencia de trazabilidad documental, no una declaración de conformidad, autorización o certificación.
- **Triestado:** `PASS`, `FAIL` y `UNKNOWN` son estados del motor de SecureCode; no se identifican directamente con los findings de SP 800-53A.

## Metodología y campos de la matriz

| # | Campo | Descripción |
|---|---|---|
| 1 | ID de control interno | Identificador GH asignado por SecureCode. |
| 2 | Nombre del control | Denominación funcional del control. |
| 3 | Rule ID | Identificador de la regla ejecutada por el motor. |
| 4 | Versión de regla | Valor de `version` en el JSON canónico. |
| 5 | Estado de regla | Valor de `active` en el JSON canónico. |
| 6 | Archivo canónico | Ruta cargada por `get_rules_directory()` / `get_rule_definition()`. |
| 7 | Evaluador | Función pública que aplica la regla. |
| 8 | Modelo de evidencia | Estructura inmutable de entrada. |
| 9 | Fuente de evidencia | Origen externo del dato observado. |
| 10 | Endpoint(s) GitHub | Rutas REST utilizadas por el adaptador. |
| 11 | Campos de evidencia | Campos permitidos y campos evaluados por la condición. |
| 12 | Condición canónica | Expresión exacta derivada del JSON canónico. |
| 13 | Resultado PASS | Condición bajo la cual el motor devuelve `PASS`. |
| 14 | Resultado FAIL | Condición bajo la cual el motor devuelve `FAIL`. |
| 15 | Control NIST SP 800-53 (parcial) | Control(es) NIST relacionados y justificación de la relación. |
| 16 | Limitaciones / estado de validación | Alcance no cubierto, matices normativos y estado de verificación documental. |

## GH-001

- **ID de control interno:** `GH-001`
- **Nombre del control:** Revisión aprobada y descarte de reseñas obsoletas en rama protegida
- **Rule ID:** `GH-001-RULE`
- **Versión de regla:** `1`
- **Estado de regla:** `active=true`
- **Archivo canónico:** `src/securecode/rules/GH-001.json`
- **Evaluador:** `evaluate_gh001`
- **Modelo de evidencia:** `GH001Evidence`
- **Fuente de evidencia:** GitHub REST API
- **Endpoints GitHub:** `GET /repos/{owner}/{repo}`, `GET /repos/{owner}/{repo}/branches/{branch}`, `GET /repos/{owner}/{repo}/branches/{branch}/protection`
- **Campos de evidencia:** permitidos `required_review_approvals`, `dismiss_stale_reviews`; evaluados `required_review_approvals`, `dismiss_stale_reviews`
- **Condición canónica:** `required_review_approvals GTE 2 AND dismiss_stale_reviews EQ true`
- **PASS:** ambos campos están presentes y `required_review_approvals >= 2` y `dismiss_stale_reviews == true`.
- **FAIL:** al menos una condición evaluable se incumple, por ejemplo `required_review_approvals < 2` o `dismiss_stale_reviews == false`; en una regla `AND`, un `FAIL` conocido prevalece sobre un `UNKNOWN` concurrente.
- **UNKNOWN:** falta evidencia, algún campo relevante es `None`, el tipo es incompatible con el operador o la evidencia global es `None`.
- **Control NIST SP 800-53 (parcial):** `CM-3 Configuration Change Control`. SP 800-53A determina si `CM-03b.[01] proposed configuration-controlled changes to the system are reviewed` y `CM-03b.[02] ... are approved or disapproved with explicit consideration for security and privacy impact analyses`. SecureCode cubre solo la verificación mecánica de que la política de rama exige aprobaciones y descarta aprobaciones obsoletas.
- **Refuerzos NIST (parciales):** `CM-3(1) Automated Documentation, Notification, and Prohibition of Changes`, especialmente `CM-03(01)(d) ... to prohibit changes to the system until designated approvals are received`, y `CM-5(4) Dual Authorization`. `CM-5(4)` es un fortalecimiento y no una equivalencia automática con el umbral interno de dos aprobaciones.
- **Métodos SP 800-53A relacionados:** `Examine` de registros de control de cambios y `Test` de mecanismos automatizados de control de cambios; SP 800-53A también contempla `Interview`, que SecureCode no realiza.
- **Limitaciones / estado de validación:** no evalúa análisis de impacto de seguridad/privacidad, identidad de aprobadores, calidad de la revisión, ni que el código aprobado corresponda al código fusionado. `2` es umbral interno. Correspondencia parcial validada documentalmente; no implica certificación.

## GH-002

- **ID de control interno:** `GH-002`
- **Nombre del control:** Protección activa de la rama por defecto
- **Rule ID:** `GH-002-RULE`
- **Versión de regla:** `1`
- **Estado de regla:** `active=true`
- **Archivo canónico:** `src/securecode/rules/GH-002.json`
- **Evaluador:** `evaluate_gh002`
- **Modelo de evidencia:** `GH002Evidence`
- **Fuente de evidencia:** GitHub REST API
- **Endpoints GitHub:** `GET /repos/{owner}/{repo}`, `GET /repos/{owner}/{repo}/branches/{default_branch}`, `GET /repos/{owner}/{repo}/branches/{default_branch}/protection`
- **Campos de evidencia:** permitidos `default_branch`, `protection_enabled`; evaluado `protection_enabled`
- **Condición canónica:** `protection_enabled EQ true`
- **PASS:** `protection_enabled == true`.
- **FAIL:** `protection_enabled == false`, por ejemplo cuando la rama existe pero el endpoint de protección devuelve `404`.
- **UNKNOWN:** `protection_enabled` es `None`, la evidencia global es `None`, el repositorio/rama no puede resolverse o la respuesta no permite decidir.
- **Control NIST SP 800-53 (parcial):** `CM-5 Access Restrictions for Change`. SP 800-53A determina si `CM-05[04] logical access restrictions associated with changes to the system are defined and documented`, `CM-05[05] ... are approved` y `CM-05[06] ... are enforced`. SecureCode observa únicamente si la protección de la rama por defecto está activa.
- **Refuerzos NIST (parciales):** `CM-5(1) Automated Access Enforcement and Audit Records`, especialmente `CM-05(01)(a) access restrictions for change are enforced using automated mechanisms`. No se evalúa la generación automática de registros de auditoría.
- **Métodos SP 800-53A relacionados:** `Examine` de configuración y registros, `Test` de mecanismos que aplican restricciones de cambio; `Interview` queda fuera del alcance de SecureCode.
- **Limitaciones / estado de validación:** `default_branch` se usa como localizador y aparece en `allowlisted_fields`, pero no forma parte de la condición. No se evalúan permisos efectivos, reglas de CODEOWNERS, restricciones de push, estado de las verificaciones obligatorias ni auditabilidad completa. Correspondencia parcial validada documentalmente; no implica certificación.

## GH-003

- **ID de control interno:** `GH-003`
- **Nombre del control:** Exigencia de commits firmados en la rama evaluada
- **Rule ID:** `GH-003-RULE`
- **Versión de regla:** `1`
- **Estado de regla:** `active=true`
- **Archivo canónico:** `src/securecode/rules/GH-003.json`
- **Evaluador:** `evaluate_gh003`
- **Modelo de evidencia:** `GH003Evidence`
- **Fuente de evidencia:** GitHub REST API
- **Endpoints GitHub:** `GET /repos/{owner}/{repo}/branches/{branch}`, `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_signatures`
- **Campos de evidencia:** permitidos `branch`, `required_signatures_enabled`; evaluado `required_signatures_enabled`
- **Condición canónica:** `required_signatures_enabled EQ true`
- **PASS:** `required_signatures_enabled == true`.
- **FAIL:** `required_signatures_enabled == false`, por ejemplo cuando el endpoint de firmas requeridas devuelve `404` para una rama existente.
- **UNKNOWN:** `required_signatures_enabled` es `None`, la evidencia global es `None`, la rama no puede resolverse o la respuesta no permite decidir.
- **Control NIST SP 800-53 (parcial):** correspondencia principal con `CM-14 Signed Components`, no con `CM-5(3)`, porque `CM-05(03)` fue retirado y trasladado a `CM-14`. SP 800-53A determina si `CM-14[01] the installation of software components is prevented unless it is verified that the software has been digitally signed using a certificate recognized and approved by the organization`. SecureCode solo verifica que GitHub exija firmas en una rama; no valida certificados, cadena de confianza ni todos los componentes.
- **Refuerzos NIST (parciales):** `SI-7 Software, Firmware, and Information Integrity` como apoyo a la integridad, junto con `SI-7(1) Integrity Checks` y `SI-7(6) Cryptographic Protection`. `SI-07(06)[01] cryptographic mechanisms are implemented to detect unauthorized changes to software` es detección de cambios no autorizados, **no** una equivalencia con commits firmados. La relación con SI-7 es de apoyo, no de cumplimiento directo.
- **Métodos SP 800-53A relacionados:** `Examine` de mecanismos criptográficos y registros, `Test` de herramientas de verificación de integridad; no se realiza `Interview`.
- **Limitaciones / estado de validación:** no verifica la firma criptográfica de cada commit, la validez del certificado, la política de firma de la organización ni la instalación de software/firmware. No existe `docs/specs/GH-003.md`; esta ficha documental cubre esa ausencia sin modificar el motor. Correspondencia parcial validada documentalmente; no implica certificación.

## Resultado de la validación normativa

- Las tres reglas canónicas están activas, tienen `version: 1` y son consistentes con los evaluadores y modelos de evidencia documentados.
- Ninguna correspondencia con NIST SP 800-53 se presenta como equivalencia plena o certificación.
- La validación se realizó contra publicaciones oficiales NIST; SP 800-53A aporta los determination statements y métodos de evaluación citados.
- Los matices críticos registrados son: umbral interno en GH-001, alcance parcial de CM-5 en GH-002 y traslado de firmas de componentes a CM-14 con apoyo indirecto de SI-7 en GH-003.
