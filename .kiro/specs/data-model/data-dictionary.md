# Diccionario de Datos del Sistema — SECURECODE

**Spec:** `.kiro/specs/data-model/data-dictionary.md`  
**Fase:** SDD — SPECIFICATION (Diccionario de Datos Lógico y Físico Auditado)  
**Fecha:** 2026-10-07  
**Estado:** PROPUESTO (Solo Documentación y Propuesta — No altera código ni migraciones)  

---

## 1. Introducción y Criterios de Auditoría

Este documento detalla el diccionario de datos de SECURECODE contrastado estrictamente contra el esquema real de PostgreSQL (migraciones `7409c81f5bf7`, `4d932f877ae7`, `1bfdcaee6d14`, `ae4b780826f2` y [`src/securecode/adapters/postgres/models.py`](file:///c:/Users/achej/Documents/SecureCode/src/securecode/adapters/postgres/models.py)).

### Precisiones Técnicas Verificadas contra Código:
1. **Defaults de Base de Datos vs Aplicación:** Las migraciones **no definen `gen_random_uuid()` ni `now()` como `server_default`** (únicamente existen `server_default='GitHub'`, `server_default='main'` y `server_default=TRUE`). Los UUIDs y marcas de tiempo son generados por la aplicación en Python (`uuid4()`, `datetime.now(timezone.utc)`).
2. **Algoritmo de Contraseñas:** Se verificó en [`src/securecode/api/security.py`](file:///c:/Users/achej/Documents/SecureCode/src/securecode/api/security.py) (líneas 8–15) que el sistema utiliza **Argon2** (`argon2.PasswordHasher()`), no bcrypt.
3. **Manejo de Usuario Inactivo:** En [`src/securecode/api/app.py`](file:///c:/Users/achej/Documents/SecureCode/src/securecode/api/app.py) (línea 52), un usuario con `active = False` genera un error **HTTP 400 Bad Request** (`detail="Inactive user"`).
4. **Restricciones CHECK:** Las restricciones `CHECK (status IN ...)` y `CHECK (length(evidence_hash) = 64)` **no existen en las migraciones actuales**; se documentan explícitamente como **[PROPUESTO]**.
5. **Lenguaje de Verificación de Integridad:** Se descartan términos como "firmas criptográficas" o "inmutabilidad absoluta/incontrovertible", adoptando la terminología precisa de **cálculo de hash determinista**, **verificación de integridad de datos** y **auditoría forense verificable**.

---

## 2. Entidad: `controls`

Catálogo maestro de políticas y controles de cumplimiento normativo (GRC).

| Columna | Tipo SQL | Nulable | PK / FK | Restricciones | Default en BD | Generación / Regla de Negocio |
|---|---|:---:|:---:|:---:|:---:|---|
| `id` | `UUID` | No | **PK** | — | Ninguno | Generado en aplicación (`uuid4()`). Clave surrogate inalterable. |
| `control_id` | `VARCHAR(50)` | No | — | `UNIQUE (uq_controls_control_id)` | Ninguno | Identificador de negocio (`GH-001`, `GH-002`). Estable una vez publicado. |
| `name` | `VARCHAR(200)` | No | — | — | Ninguno | Nombre descriptivo legible en interfaces de usuario y reportes. |
| `description` | `TEXT` | Sí | — | — | `NULL` | Justificación técnica y objetivo de seguridad del control. |
| `source_type` | `VARCHAR(50)` | No | — | — | `'GitHub'` | Conector de recolección (`server_default='GitHub'`). |
| `active` | `BOOLEAN` | No | — | — | `TRUE` | Vigencia operativa (`server_default=TRUE`). Soft deprecation. |
| `created_at` | `TIMESTAMPTZ` | No | — | — | Ninguno | Asignado en aplicación (`datetime.now(timezone.utc)`). |
| `updated_at` | `TIMESTAMPTZ` | No | — | — | Ninguno | Asignado en aplicación al actualizar metadatos. |
| `tenant_id` | `UUID` | Sí | — | — | `NULL` | Multi-tenancy preparatoria. `NULL` = control global compartido. |
| `severity` *(PROPUESTO)* | `VARCHAR(20)` | No | — | `[PROPUESTO] CHECK (severity IN ('HIGH', 'MEDIUM', 'LOW'))` | Ninguno | **[DECISIÓN PENDIENTE]** Nivel de impacto del control (ver `gaps.md`). Si se aprueba, se migra en tres pasos (ADD NULL, UPDATE, SET NOT NULL). |
| `framework` *(PROPUESTO)* | `VARCHAR(100)` | Sí | — | — | `NULL` | Marco de referencia regulatorio (ej. CIS, ISO 27001). Referencias a PR.IP-1: **pendiente de verificar contra NIST CSWP.29**. |

### Índices de `controls`:
- `pk_controls` (PRIMARY KEY en `id`)
- `uq_controls_control_id` (UNIQUE en `control_id`)
- `idx_controls_control_id` (B-tree en `control_id`)
- `idx_controls_source_type` (B-tree en `source_type`)
- `idx_controls_active` (B-tree en `active`)
- `idx_controls_tenant_id` (B-tree en `tenant_id`)

---

## 3. Entidad: `rules`

Historial versionado de reglas declarativas deterministas vinculadas a cada control.

| Columna | Tipo SQL | Nulable | PK / FK | Restricciones | Default en BD | Generación / Regla de Negocio |
|---|---|:---:|:---:|:---:|:---:|---|
| `id` | `UUID` | No | **PK** | — | Ninguno | Generado en aplicación (`uuid4()`). |
| `rule_id` | `VARCHAR(100)` | No | — | — | Ninguno | Identificador funcional de la regla (ej. `GH-001-RULE`). |
| `control_id` | `VARCHAR(50)` | No | **FK** | `FK -> controls.control_id` | Ninguno | `ON UPDATE CASCADE ON DELETE RESTRICT`. Un control puede tener múltiples reglas asociadas. |
| `version` | `INTEGER` | No | — | — | Ninguno | Versión secuencial de la regla ($1, 2 \dots$). |
| `active` | `BOOLEAN` | No | — | — | `TRUE` | `server_default=TRUE`. |
| `condition` | `JSONB` | No | — | — | Ninguno | Árbol lógico determinista de evaluación. |
| `allowlisted_fields` | `JSONB` | No | — | — | Ninguno | Campos permitidos en la evidencia normalizada. |
| `created_at` | `TIMESTAMPTZ` | No | — | — | Ninguno | Asignado en aplicación (`datetime.now(timezone.utc)`). |
| `tenant_id` | `UUID` | Sí | — | — | `NULL` | `NULL` = regla canónica global. |

### Restricciones e Índices de `rules`:
- `pk_rules` (PRIMARY KEY en `id`)
- `uq_rules_rule_version` (UNIQUE en `(rule_id, version)`)
- `fk_rules_control_id` (`FOREIGN KEY (control_id) REFERENCES controls(control_id) ON UPDATE CASCADE ON DELETE RESTRICT`)
- `idx_rules_control_id` (B-tree en `control_id`)
- `idx_rules_rule_id` (B-tree en `rule_id`)
- `idx_rules_active` (B-tree en `active`)
- `idx_rules_tenant_id` (B-tree en `tenant_id`)
- `uq_rules_one_active_per_rule` (**PROPUESTO MVP:** `UNIQUE INDEX ON rules (rule_id) WHERE active = TRUE`):
  * *Ajuste Arquitectónico e Identificadores Reales:* Un control se vincula a su regla correspondiente (ej. control `GH-001` con regla canónica `GH-001-RULE`, y control `GH-002` con `GH-002-RULE`). Si en el futuro un control requiriese evaluar múltiples reglas concurrentes, un índice por `(control_id)` restringiría indebidamente el modelo; por ello se restringe estrictamente por **`(rule_id)`**, garantizando que para una regla dada exista únicamente una versión activa a la vez.
  * *Por qué se define exclusivamente como `(rule_id) WHERE active = TRUE` para el MVP y no se usa `(rule_id, tenant_id)` mientras `tenant_id` sea `NULL`:*
    En el estándar SQL implementado por PostgreSQL y SQLite, cada valor `NULL` se considera distinto a otro `NULL` (`NULL != NULL`). Por lo tanto, un índice único sobre `(rule_id, tenant_id) WHERE active = TRUE` **no impediría filas duplicadas** cuando `tenant_id` es `NULL`, permitiendo que coexistan múltiples versiones activas de la misma regla global (`GH-001-RULE` o `GH-002-RULE`). Dado que en el MVP todas las reglas son globales y tienen `tenant_id = NULL`, incluir `tenant_id` en el índice anularía por completo la garantía de unicidad. Por ello, para el MVP el índice debe ser exclusivamente sobre `(rule_id) WHERE active = TRUE`. Cuando se introduzca multi-tenancy formal en el futuro con tenants aislados, se migrará a índices parciales segregados por tenant o se utilizará `NULLS NOT DISTINCT` (PostgreSQL 15+).

---

## 4. Entidad: `sources`

Registro de activos tecnológicos bajo alcance de evaluación (repositorios SCM).

| Columna | Tipo SQL | Nulable | PK / FK | Restricciones | Default en BD | Generación / Regla de Negocio |
|---|---|:---:|:---:|:---:|:---:|---|
| `id` | `UUID` | No | **PK** | — | Ninguno | Generado en aplicación (`uuid4()`). |
| `source_type` | `VARCHAR(50)` | No | — | — | `'GitHub'` | `server_default='GitHub'`. |
| `owner` | `VARCHAR(255)` | No | — | — | Ninguno | Propietario u organización en GitHub. |
| `repository` | `VARCHAR(255)` | No | — | — | Ninguno | Nombre del repositorio auditado. |
| `default_branch` | `VARCHAR(255)` | No | — | — | `'main'` | `server_default='main'`. Utilizada por `GH-002`. |
| `active` | `BOOLEAN` | No | — | — | `TRUE` | `server_default=TRUE`. |
| `connected_at` | `TIMESTAMPTZ` | No | — | — | Ninguno | Asignado en aplicación al conectar el repositorio. |
| `last_checked_at` | `TIMESTAMPTZ` | Sí | — | — | `NULL` | Se actualiza en cada ejecución de evaluación. |
| `tenant_id` | `UUID` | Sí | — | — | `NULL` | `NULL` = repositorio global. |

### Restricciones e Índices de `sources`:
- `pk_sources` (PRIMARY KEY en `id`)
- **Reemplazo de la restricción `UNIQUE` original por Índices Parciales:**  
  La restricción original de la migración `uq_sources_repo_tenant` (`UNIQUE (source_type, owner, repository, tenant_id)`) **debe ser eliminada y reemplazada** por dos índices únicos parciales. Esto es estrictamente necesario porque en PostgreSQL y SQLite los valores `NULL` no deduplican (`NULL != NULL`), lo que permitía insertar repositorios globales duplicados donde `tenant_id IS NULL`.
  - `uq_sources_repo_global` (**PROPUESTO:** `UNIQUE INDEX ON sources (source_type, owner, repository) WHERE tenant_id IS NULL`) — Reemplaza la unicidad para fuentes globales en el MVP.
  - `uq_sources_repo_tenant_partial` (**PROPUESTO:** `UNIQUE INDEX ON sources (source_type, owner, repository, tenant_id) WHERE tenant_id IS NOT NULL`) — Garantiza unicidad por tenant para evolución futura.
  - **Declaración en SQLAlchemy (`models.py`) y Alembic:**  
    Para asegurar compatibilidad dual tanto en el entorno productivo (PostgreSQL) como en la suite de pruebas unitarias y de integración local en CI (SQLite), estos índices parciales **deben declararse explícitamente en el modelo SQLAlchemy utilizando `postgresql_where` y `sqlite_where`**:
    ```python
    Index(
        'uq_sources_repo_global',
        'source_type', 'owner', 'repository',
        unique=True,
        postgresql_where=text("tenant_id IS NULL"),
        sqlite_where=text("tenant_id IS NULL"),
    ),
    Index(
        'uq_sources_repo_tenant_partial',
        'source_type', 'owner', 'repository', 'tenant_id',
        unique=True,
        postgresql_where=text("tenant_id IS NOT NULL"),
        sqlite_where=text("tenant_id IS NOT NULL"),
    )
    ```
- `idx_sources_owner_repo` (B-tree en `(owner, repository)`)
- `idx_sources_source_type` (B-tree en `source_type`)
- `idx_sources_active` (B-tree en `active`)
- `idx_sources_tenant_id` (B-tree en `tenant_id`)

---

## 5. Entidad: `evidence_records`

Repositorio de telemetría normalizada y hashes de verificación de integridad.

| Columna | Tipo SQL | Nulable | PK / FK | Restricciones | Default en BD | Generación / Regla de Negocio |
|---|---|:---:|:---:|:---:|:---:|---|
| `id` | `UUID` | No | **PK** | — | Ninguno | Generado en aplicación (`uuid4()`). |
| `control_id` | `VARCHAR(50)` | No | — | — | Ninguno | Control evaluado (`GH-001`, `GH-002`). |
| `evidence_hash` | `VARCHAR(64)` | No | — | `[PROPUESTO] CHECK (length(evidence_hash) = 64)` | Ninguno | Hash SHA-256 canónico de los **campos normalizados**. |
| `raw_evidence` | `JSONB` | No | — | — | Ninguno | JSON estructurado con los **campos normalizados ya extraídos**. |
| `collected_at` | `TIMESTAMPTZ` | No | — | — | Ninguno | Asignado en aplicación (`datetime.now(timezone.utc)`). |
| `tenant_id` | `UUID` | Sí | — | — | `NULL` | `NULL` = sin tenant / global. |

### Precisión Crítica: Alcance del Hash y Naturaleza de `raw_evidence`
1. **Alcance del Hash Canónico:**
   * En `GH001Evidence.canonical_hash()`: entran estrictamente `control`, `dismiss_stale_reviews` y `required_review_approvals`.
   * En `GH002Evidence.canonical_hash()`: entran estrictamente `control`, `default_branch` y `protection_enabled`.
   * **El hash cubre únicamente los campos normalizados; no identifica el repositorio, la rama ni el momento temporal (`collected_at`).**
2. **Contenido Real de `raw_evidence` e Implicación para HU-06:**
   * Según se verifica en [`src/securecode/adapters/postgres/repository.py`](file:///c:/Users/achej/Documents/SecureCode/src/securecode/adapters/postgres/repository.py) (líneas 37–40 y 88–91), la columna `raw_evidence` **no almacena el payload crudo HTTP devuelto por GitHub** (headers, JSON anidado original con URLs y metadata de GitHub), sino que almacena un diccionario con los **campos normalizados ya parseados**.
   * *Implicación para HU-06:* La HU-06 (visor de JSON crudo de GitHub) queda clasificada como **NO SATISFECHA con el esquema actual**. Se proponen dos vías de resolución:
     - **Opción 1 (MVP):** Reescribir el Escenario 2 de la HU-06 para presentar la evidencia estructurada normalizada en formato JSON.
     - **Opción 2 (Evolución Futura):** Persistir el payload HTTP original devuelto por GitHub, lo que requiere adaptar el conector y revisar minuciosamente la política de cero secretos para prevenir el almacenamiento de tokens o credenciales.

### Decisión de Unicidad: Adopción de Alternativa B (Sin Deduplicar)
*(Estado: **Pendiente de confirmar con Jonathann**)*

1. **Diagnóstico del Conflicto:**
   Dado que el hash no contiene el repositorio ni el timestamp, dos repositorios distintos con configuraciones idénticas de branch protection producen el mismo `evidence_hash`. Si existe un constraint `UNIQUE` sobre `(control_id, evidence_hash, tenant_id)`, la segunda evaluación falla con `IntegrityError` porque `evaluate_and_store_*` ejecuta un `INSERT` incondicional con un nuevo `evidence_id = uuid4()`.
2. **Decisión Adoptada (Alternativa B):**
   * **Se suelta la unicidad en `evidence_records`**. Cada evaluación genera su propio registro de evidencia asociado, preservando fielmente su propio `collected_at` sin distorsión temporal.
3. **Migración Propuesta:**
   ```sql
   -- Eliminar índice único existente
   DROP INDEX IF EXISTS uq_evidence_control_hash;
   -- Crear índice B-tree ordinario (no único) para acelerar búsquedas forenses por hash
   CREATE INDEX idx_evidence_control_hash ON evidence_records (control_id, evidence_hash);
   ```
4. **Impacto en el Código y Test Bench:**
   * **En `src/securecode/adapters/postgres/models.py`:** En `EvidenceRecord.__table_args__`, reemplazar `Index('uq_evidence_control_hash', ..., unique=True)` por `Index('idx_evidence_control_hash', 'control_id', 'evidence_hash')`.
   * **En Test 3 de TASK-05 (`database-schema` / `tests/integration/test_migrations.py`):** El test `test_unique_evidence_hash_per_tenant` esperaba un `IntegrityError` al insertar dos evidencias idénticas. Bajo la Alternativa B, **dicho test debe ser actualizado** para verificar que la inserción de múltiples evidencias con el mismo hash es permitida y válida.

### Índices Propuestos de `evidence_records`:
- `pk_evidence_records` (PRIMARY KEY en `id`)
- `idx_evidence_control_hash` (**PROPUESTO:** B-tree no único en `(control_id, evidence_hash)`)
- `idx_evidence_control_id` (B-tree en `control_id`)
- `idx_evidence_collected_at` (B-tree en `collected_at`)
- `idx_evidence_tenant_id` (B-tree en `tenant_id`)

---

## 6. Entidad: `evaluation_records`

Bitácora de auditoría histórica con veredictos formales de evaluación determinista.

| Columna | Tipo SQL | Nulable | PK / FK | Restricciones | Default en BD | Generación / Regla de Negocio |
|---|---|:---:|:---:|:---:|:---:|---|
| `id` | `UUID` | No | **PK** | — | Ninguno | Generado en aplicación (`uuid4()`). |
| `control_id` | `VARCHAR(50)` | No | — | — | Ninguno | Identificador de negocio (`GH-001`, `GH-002`). |
| `rule_id` | `VARCHAR(100)` | Sí | — | — | `NULL` | Trazabilidad de regla aplicada (migración `4d932f877ae7`). |
| `rule_version` | `INTEGER` | Sí | — | — | `NULL` | Versión específica de la regla ejecutada. |
| `status` | `VARCHAR(50)` | No | — | `[PROPUESTO] CHECK (status IN ('PASS', 'FAIL', 'UNKNOWN'))` | Ninguno | Veredicto formal emitido por el motor determinista. |
| `unknown_reason` *(PROPUESTO)* | `VARCHAR(100)` | Sí | — | `[PROPUESTO]` Vocabulario cerrado + CHECK de coherencia relajado | `NULL` | Causa de evidencia insuficiente (`INCOMPLETE_EVIDENCE`, `INSUFFICIENT_TOKEN_SCOPES`, etc.). |
| `evaluated_at` | `TIMESTAMPTZ` | No | — | — | Ninguno | Asignado en aplicación (`datetime.now(timezone.utc)`). |
| `evidence_id` | `UUID` | No | **FK** | `FK -> evidence_records.id` | Ninguno | Vínculo mandatorio a la evidencia que respalda el veredicto. |
| `requested_by_user_id` | `UUID` | Sí | **FK** | `FK -> users.id` | `NULL` | Usuario que disparó la evaluación on-demand (`1bfdcaee6d14`). |
| `source_type` | `VARCHAR(50)` | No | — | — | Ninguno | Tipo de origen (`'GitHub'`). |
| `source_repository` | `VARCHAR(255)` | No | — | — | Ninguno | **Texto histórico inalterable preservado** (ej. `owner/repo`). |
| `source_branch` | `VARCHAR(255)` | No | — | — | Ninguno | **Texto histórico inalterable preservado** (ej. `main`). |
| `source_id` *(PROPUESTO)* | `UUID` | Sí | **FK** | `[PROPUESTO] FK -> sources.id ON DELETE SET NULL` | `NULL` | Clave foránea opcional a la fuente registrada. |
| `tenant_id` | `UUID` | Sí | — | — | `NULL` | Preparación multi-tenancy. |

### Restricciones Propuestas para `evaluation_records`:
1. **Vocabulario Cerrado para `unknown_reason` (con `INCOMPLETE_EVIDENCE`):**
   ```sql
   CONSTRAINT chk_eval_unknown_reason_vocab CHECK (
       unknown_reason IS NULL OR unknown_reason IN (
           'INCOMPLETE_EVIDENCE',
           'INSUFFICIENT_TOKEN_SCOPES',
           'RESOURCE_NOT_FOUND',
           'RATE_LIMITED',
           'SCHEMA_MISMATCH',
           'UNAUTHENTICATED',
           'PUBLIC_ENDPOINT_RESTRICTION'
       )
   )
   ```
2. **CHECK de Coherencia Relajado (Imprescindible para compatibilidad):**
   ```sql
   CONSTRAINT chk_eval_unknown_reason_coherence CHECK (
       status = 'UNKNOWN' OR unknown_reason IS NULL
   )
   ```
   > **Por qué la versión bidireccional rompía datos legacy y endpoints:**
   > - *Datos Legacy:* Todos los registros históricos con `status = 'UNKNOWN'` tienen `unknown_reason IS NULL`. La versión bidireccional (`status = 'UNKNOWN' AND unknown_reason IS NOT NULL`) habría invalidado todas las filas existentes en la base de datos al aplicar la migración.
   > - *Endpoints Actuales:* [`app.py`](file:///c:/Users/achej/Documents/SecureCode/src/securecode/api/app.py) ejecuta `evaluate_and_store_*`, funciones que hoy no reciben ni insertan `unknown_reason`. Si la regla fuera bidireccional, cualquier evaluación que resulte en `UNKNOWN` fallaría con `IntegrityError` en producción.
   > - *Comportamiento Relajado:* Garantiza que un `PASS` o `FAIL` **nunca** tenga un `unknown_reason`, pero permite que un `UNKNOWN` tenga `NULL` (compatibilidad legacy y endpoints no migrados).

### Índices de `evaluation_records`:
- `pk_evaluation_records` (PRIMARY KEY en `id`)
- `fk_evaluation_evidence` (`FOREIGN KEY (evidence_id) REFERENCES evidence_records(id)`)
- `fk_evaluation_user` (`FOREIGN KEY (requested_by_user_id) REFERENCES users(id)`)
- `idx_eval_control_id` (B-tree en `control_id`)
- `idx_eval_status` (B-tree en `status`)
- `idx_eval_unknown_reason` (**PROPUESTO:** B-tree en `unknown_reason`)
- `idx_eval_evaluated_at` (B-tree en `evaluated_at`)
- `idx_eval_source_repo` (B-tree en `source_repository`)
- `idx_eval_source_id` (**PROPUESTO:** B-tree en `source_id`)
- `idx_eval_rule_id` (B-tree en `rule_id`)
- `idx_eval_tenant_id` (B-tree en `tenant_id`)

---

## 7. Entidad: `users`

Identidades de usuarios autorizados para operar la plataforma y consumir la API.

| Columna | Tipo SQL | Nulable | PK / FK | Restricciones | Default en BD | Generación / Regla de Negocio |
|---|---|:---:|:---:|:---:|:---:|---|
| `id` | `UUID` | No | **PK** | — | Ninguno | Generado en aplicación (`uuid4()`). |
| `username` | `VARCHAR(100)` | No | — | `UNIQUE` | Ninguno | Identificador único de credencial. |
| `password_hash` | `VARCHAR(255)` | No | — | — | Ninguno | **Hash generado con Argon2** (`argon2.PasswordHasher`). |
| `active` | `BOOLEAN` | No | — | — | Ninguno | Estado de la cuenta. Si es `FALSE`, `POST /api/v1/auth/token` retorna **HTTP 400 Bad Request**. |
| `created_at` | `TIMESTAMPTZ` | No | — | — | Ninguno | Asignado en aplicación (`datetime.now(timezone.utc)`). |
| `role` *(PROPUESTO)* | `VARCHAR(50)` | No | — | `[PROPUESTO] CHECK (role IN ('admin', 'grc_analyst', 'devsecops', 'ciso', 'auditor', 'viewer'))` | `'viewer'` | Requerido por HU-01 para habilitar o restringir vistas según perfil. |

### Restricciones e Índices de `users`:
- `pk_users` (PRIMARY KEY en `id`)
- `uq_users_username` (UNIQUE CONSTRAINT en `username`)
