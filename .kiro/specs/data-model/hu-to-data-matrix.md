# Matriz de Trazabilidad HU → Datos — SECURECODE

**Spec:** `.kiro/specs/data-model/hu-to-data-matrix.md`  
**Fase:** SDD — SPECIFICATION (Contraste Funcional vs Esquema de Datos Auditado)  
**Fecha:** 2026-10-07  
**Estado:** PROPUESTO (Solo Documentación y Propuesta — No altera código ni migraciones)  

---

## 1. Resumen y Criterio de Clasificación

Para cada Historia de Usuario (HU-01 a HU-10), se identifican las entidades y atributos que consume la interfaz web. Cada campo se clasifica en una de tres categorías estrictas:

- **EXISTE:** El campo reside formalmente en el esquema actual de PostgreSQL (`models.py` / migraciones Alembic).
- **DERIVADO:** El dato no se almacena como una columna directa, sino que se calcula mediante una consulta SQL agregada (`COUNT`, `GROUP BY`, fórmulas) o proyección en tiempo de ejecución.
- **FALTA (PROPUESTO):** El dato es requerido por la experiencia de usuario o la regla de negocio de la HU, pero no existe en el esquema actual y requiere migración/definición formal.

En todo el documento se utiliza estrictamente el nombre real de la tabla: **`evaluation_records`**.

---

## 2. Matriz Detallada por Historia de Usuario

### HU-01: Autenticación de Usuario Corporativo
* **Actor:** Analista GRC (y resto de actores)
* **Pantalla:** `Pantalla de Login`
* **Consumo de Datos:**
  | Entidad | Campo Requerido | Estado | Detalle / Justificación |
  |---|---|:---:|---|
  | `users` | `username` | **EXISTE** | Utilizado para identificar al usuario en `POST /api/v1/auth/token`. |
  | `users` | `password_hash` | **EXISTE** | Validado internamente con Argon2 (`argon2.PasswordHasher`). |
  | `users` | `active` | **EXISTE** | Valida si el usuario está habilitado para operar (si es `False`, API retorna HTTP 400). |
  | `users` | `role` | **FALTA (PROPUESTO)** | Columna `role VARCHAR(50) DEFAULT 'viewer'` con `[PROPUESTO] CHECK (role IN ('admin', 'grc_analyst', 'devsecops', 'ciso', 'auditor', 'viewer'))`. Necesario para adaptar la UI y ocultar botones de ejecución al auditor. |

---

### HU-02: Visualización de Postura Global de Cumplimiento
* **Actor:** CISO
* **Pantalla:** `Pantalla de Dashboard Ejecutivo`
* **Consumo de Datos:**
  | Entidad | Campo Requerido | Estado | Detalle / Justificación |
  |---|---|:---:|---|
  | `evaluation_records` | Total de Evaluaciones | **DERIVADO** | `COUNT(id)` sobre la tabla `evaluation_records`. |
  | `evaluation_records` | Conteo de `PASS` | **DERIVADO** | `COUNT(*) FILTER (WHERE status = 'PASS')`. |
  | `evaluation_records` | Conteo de `FAIL` | **DERIVADO** | `COUNT(*) FILTER (WHERE status = 'FAIL')`. |
  | `evaluation_records` | Conteo de `UNKNOWN` | **DERIVADO** | `COUNT(*) FILTER (WHERE status = 'UNKNOWN')`. Representa evidencia insuficiente. |
  | `evaluation_records` | Compliance Score (%) | **DERIVADO** | $(\text{Total PASS} / (\text{Total PASS} + \text{Total FAIL})) \times 100$. Excluye UNKNOWN del cálculo binario. |
  | `evaluation_records` | Repositorios Evaluados | **DERIVADO** | `COUNT(DISTINCT source_repository)` sobre `evaluation_records`. |
  | `evaluation_records` | Última Fecha de Corte | **DERIVADO** | `MAX(evaluated_at)` sobre `evaluation_records`. |

---

### HU-03: Exploración del Catálogo de Controles de Seguridad
* **Actor:** Analista GRC
* **Pantalla:** `Pantalla de Catálogo de Controles`
* **Consumo de Datos:**
  | Entidad | Campo Requerido | Estado | Detalle / Justificación |
  |---|---|:---:|---|
  | `controls` | `control_id` | **EXISTE** | Identificador de negocio (`GH-001`, `GH-002`). |
  | `controls` | `name` | **EXISTE** | Nombre oficial legible del control. |
  | `controls` | `description` | **EXISTE** | Descripción del objetivo de seguridad. |
  | `controls` | `active` | **EXISTE** | Filtro de vigencia del control. |
  | `rules` | `rule_id` | **EXISTE** | Identificador de la regla determinista. |
  | `rules` | `version` | **EXISTE** | Versión activa de la regla. |
  | `rules` | `condition` | **EXISTE** | JSONB con los umbrales deterministas del oráculo. |
  | `controls` | `severity` | **FALTA (PROPUESTO)** | `VARCHAR(20) NOT NULL` **sin DEFAULT** (`[PROPUESTO] CHECK IN ('HIGH', 'MEDIUM', 'LOW')` — alineado con HU-03 sin 'CRITICAL'). Asignación explícita requerida para evitar riesgos enmascarados. |
  | `controls` | `framework` | **FALTA (PROPUESTO)** | `VARCHAR(100) NULL`. Referencia a estándar regulatorio (ej. CIS GitHub Foundations, SOC 2 CC8.1, ISO 27001). Referencias a PR.IP-1: **pendiente de verificar contra NIST CSWP.29**. |

---

### HU-04: Ejecución de Evaluación de Control Bajo Demanda
* **Actor:** Ingeniero DevSecOps
* **Pantalla:** `Modal de Nueva Evaluación`
* **Consumo de Datos:**
  | Entidad | Campo Requerido | Estado | Detalle / Justificación |
  |---|---|:---:|---|
  | `controls` | `control_id` | **EXISTE** | Selección del control a ejecutar. |
  | `sources` | `repository`, `owner` | **EXISTE** | Selección o entrada del target en GitHub. |
  | `evaluation_records` | `status` | **EXISTE** | Resultado devuelto (`PASS`, `FAIL`, `UNKNOWN`). |
  | `evaluation_records` | `requested_by_user_id`| **EXISTE** | Usuario autenticado asociado a la corrida. |
  | `evidence_records` | `evidence_hash` | **EXISTE** | Hash SHA-256 generado atómicamente. |
  | `evidence_records` | `raw_evidence` | **EXISTE** | Telemetría obtenida desde GitHub API. |
  | Parámetro runtime | `X-GitHub-Token` | **N/A** | No se persiste en base de datos; se envía como cabecera efímera en la llamada HTTP. |

---

### HU-05: Bitácora Histórica y Auditoría de Evaluaciones
* **Actor:** Auditor externo
* **Pantalla:** `Pantalla de Historial de Evaluaciones`
* **Consumo de Datos:**
  | Entidad | Campo Requerido | Estado | Detalle / Justificación |
  |---|---|:---:|---|
  | `evaluation_records` | `evaluated_at` | **EXISTE** | Fecha y hora de la evaluación. |
  | `evaluation_records` | `source_repository` | **EXISTE** | Nombre del repositorio auditado (texto inmutable). |
  | `evaluation_records` | `source_branch` | **EXISTE** | Rama auditada (texto inmutable). |
  | `evaluation_records` | `control_id` | **EXISTE** | Control evaluado. |
  | `evaluation_records` | `status` | **EXISTE** | Estado tri-estado. |
  | `evidence_records` | `evidence_hash` | **EXISTE** | Hash SHA-256 de 64 caracteres hex. |
  | `evaluation_records` | Paginación / Total | **DERIVADO** | `COUNT(*)` y clauses `LIMIT / OFFSET`. |

---

### HU-06: Verificación de Evidencia e Integridad (SHA-256) / Visor de JSON
* **Actor:** Auditor externo
* **Pantalla:** `Pantalla de Detalle de Evaluación`
* **Estado de Cumplimiento:** **NO SATISFECHA (con el esquema actual para el visor de JSON crudo de GitHub)**.
  > **Diagnóstico del Requerimiento:**  
  > El Escenario 2 de la HU-06 solicita que el auditor inspeccione el *payload JSON crudo retornado por GitHub*. Sin embargo, el esquema actual en PostgreSQL almacena en `evidence_records.raw_evidence` únicamente un diccionario con los **campos normalizados ya extraídos** (`required_review_approvals`, `dismiss_stale_reviews`, etc.), y **no el payload HTTP crudo devuelto por la API de GitHub**. Por consiguiente, la necesidad de inspeccionar el JSON original no está cubierta por la base de datos actual.
  >
  > **Opciones de Resolución:**
  > - **Opción 1 (Recomendada para MVP):** Reescribir el Escenario 2 de la HU-06 para que el visor presente la **evidencia estructurada normalizada** en formato JSON (que es lo que realmente persiste `raw_evidence`). Permite verificar la integridad de los datos sobre los que corrió la regla determinista sin modificar adaptadores ni arriesgar fuga de credenciales.
  > - **Opción 2 (Evolución Futura):** Persistir el **payload HTTP original devuelto por GitHub** (agregando por ejemplo una columna `github_http_payload` en `evidence_records`). Esta opción requiere: (1) modificar los adaptadores (`github_adapter.py`) para capturar la respuesta HTTP no parseada, y (2) una exhaustiva revisión de la **política de cero secretos** para asegurar que no se persistan tokens, cabeceras sensibles, URLs con credenciales o metadatos no autorizados en la base de datos.
* **Consumo de Datos:**
  | Entidad | Campo Requerido | Estado | Detalle / Justificación |
  |---|---|:---:|---|
  | `evaluation_records` | `id` | **EXISTE** | UUID de la evaluación auditada. |
  | `evaluation_records` | `rule_id`, `rule_version`| **EXISTE** | Versión exacta de la regla aplicada (ej. `GH-001-RULE`, `GH-002-RULE`). |
  | `evidence_records` | `evidence_hash` | **EXISTE** | Hash canónico SHA-256 de 64 caracteres hex. |
  | `evidence_records` | `raw_evidence` | **EXISTE (Parcial)** | JSONB que almacena exclusivamente los campos normalizados ya extraídos (NO el JSON crudo HTTP de GitHub). Satisface la Opción 1 (MVP); no cubre la Opción 2. |
  | `evidence_records` | `collected_at` | **EXISTE** | Timestamp de captura (preservado individualmente por Alternativa B sin deduplicación). |
  | `evidence_records` | Payload crudo HTTP GitHub | **FALTA** | No existe en base de datos. Requiere Opción 2 (Evolución futura). |

---

### HU-07: Diagnóstico y Causa Raíz de Estado UNKNOWN
* **Actor:** Ingeniero DevSecOps
* **Pantalla:** `Pantalla de Detalle de Evaluación`
* **Consumo de Datos:**
  | Entidad | Campo Requerido | Estado | Detalle / Justificación |
  |---|---|:---:|---|
  | `evaluation_records` | `status == 'UNKNOWN'` | **EXISTE** | Disparador de la vista de diagnóstico no punitiva. |
  | `evidence_records` | `raw_evidence` | **EXISTE** | Contiene los campos nulos que originaron la falta de evidencia. |
  | `evaluation_records` | `unknown_reason` | **FALTA (PROPUESTO)** | **Columna formal con vocabulario cerrado (`INCOMPLETE_EVIDENCE`, `INSUFFICIENT_TOKEN_SCOPES`, `RESOURCE_NOT_FOUND`, `RATE_LIMITED`, `SCHEMA_MISMATCH`, `UNAUTHENTICATED`, `PUBLIC_ENDPOINT_RESTRICTION`) y CHECK de coherencia relajado (`status = 'UNKNOWN' OR unknown_reason IS NULL`)**. Garantiza que `PASS` y `FAIL` nunca tengan causa, tolerando `NULL` en `UNKNOWN` para compatibilidad regresiva con datos legacy y endpoints actuales. |

---

### HU-08: Guía de Remediación Técnica ante Incumplimiento (FAIL)
* **Actor:** Ingeniero DevSecOps
* **Pantalla:** `Pantalla de Detalle de Evaluación`
* **Consumo de Datos:**
  | Entidad | Campo Requerido | Estado | Detalle / Justificación |
  |---|---|:---:|---|
  | `evaluation_records` | `status == 'FAIL'` | **EXISTE** | Identificador de no conformidad. |
  | `evidence_records` | `raw_evidence` | **EXISTE** | Valores reales (ej. `required_review_approvals: 1`). |
  | `rules` | `condition` | **EXISTE** | Umbrales exigidos (ej. `required_review_approvals >= 2`). |
  | Parámetro Incumplido | Brecha de configuración | **DERIVADO** | Se deduce comparando `raw_evidence` contra `condition`. |
  | Capa Frontend | Pasos de remediación | **FRONTEND ONLY** | **Decisión adoptada:** La guía de remediación y enlaces a GitHub se gestionan 100% en el frontend. No requiere columnas en la base de datos (GAP-04 eliminado del esquema). |

---

### HU-09: Catálogo de Fuentes y Repositorios Conectados
* **Actor:** Administrador
* **Pantalla:** `Pantalla de Fuentes Conectadas`
* **Consumo de Datos:**
  | Entidad | Campo Requerido | Estado | Detalle / Justificación |
  |---|---|:---:|---|
  | `sources` | `owner`, `repository` | **EXISTE** | Coordenadas del repositorio GitHub. |
  | `sources` | `source_type` | **EXISTE** | Conector (`GitHub`). |
  | `sources` | `default_branch` | **EXISTE** | Rama principal. |
  | `sources` | `connected_at` | **EXISTE** | Fecha de vinculación. |
  | `sources` | `last_checked_at` | **EXISTE** | Timestamp de última evaluación. |
  | `sources` | Conteo de evaluaciones | **DERIVADO** | `COUNT(evaluation_records)` agrupado por repositorio. |
  | `evaluation_records` | `source_id` | **FALTA (PROPUESTO)** | **Decisión adoptada:** `source_id UUID NULL FK -> sources.id`. Coexiste con `source_repository` y `source_branch` (preservados como texto histórico inmutable). |

---

### HU-10: Exportación de Evidencia de Cumplimiento
* **Actor:** Auditor externo
* **Pantalla:** `Pantalla de Historial de Evaluaciones`
* **Consumo de Datos:**
  | Entidad | Campo Requerido | Estado | Detalle / Justificación |
  |---|---|:---:|---|
  | `evaluation_records` | Registro consolidado | **EXISTE** | Columnas de auditoría (`id`, `control_id`, `status`, `evaluated_at`). |
  | `evidence_records` | `evidence_hash` | **EXISTE** | Firma criptográfica SHA-256. |
  | Exportable CSV/JSON | Archivo generado | **DERIVADO** | Proyección de consulta o serialización client-side. |

---

## 3. Síntesis de Faltantes y Correcciones Técnicas

1. **Severidad obligatoria sin default (`controls.severity` - HU-03):** Se alinea a `('HIGH', 'MEDIUM', 'LOW')` sin 'CRITICAL'. Se establece procedimiento de migración en 4 pasos (ADD NULL -> UPDATE -> SET NOT NULL + CHECK).
2. **Mapeo normativo (`controls.framework` - HU-03):** Referencia a `PR.IP-1` marcada formalmente como *"pendiente de verificar contra NIST CSWP.29"*.
3. **Causa `UNKNOWN` estructurada (`evaluation_records.unknown_reason` - HU-07):** Incorpora `INCOMPLETE_EVIDENCE` y CHECK de coherencia relajado (`status = 'UNKNOWN' OR unknown_reason IS NULL`).
4. **Remediación ante `FAIL` (HU-08):** Descartada del esquema de datos. Resuelta en cliente/frontend.
5. **Relación Evaluaciones ↔ Fuentes (`evaluation_records.source_id` - HU-09):** Resuelto como FK nullable con persistencia redundante de texto histórico.
6. **Unicidad de `evidence_records` (Decisión Pendiente):** Documentada la prueba de colisión entre repositorios idénticos y el dilema entre deduplicación vs preservación de `collected_at` para HU-06.
