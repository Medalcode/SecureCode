# Análisis de Brechas del Esquema de Datos (Gaps) — SECURECODE

**Spec:** `.kiro/specs/data-model/gaps.md`  
**Fase:** SDD — SPECIFICATION (Análisis de Gaps y Decisiones Incorporadas)  
**Fecha:** 2026-10-07  
**Estado:** PROPUESTO (Solo Documentación y Propuesta — No altera código ni migraciones)  

---

## 1. Introducción

Este documento recopila las diferencias entre el esquema físico actual de la base de datos de SECURECODE (PostgreSQL / Alembic) y los requerimientos funcionales del frontend MVP derivados de las Historias de Usuario HU-01 a HU-10, incorporando las decisiones de diseño arquitectónicas y la auditoría exhaustiva del código fuente.

En todo el documento se utiliza estrictamente el nombre real de la tabla: **`evaluation_records`**. Se aplica un lenguaje riguroso de **verificación de integridad** (evitando términos como "firmas criptográficas" o "inmutabilidad absoluta/incontrovertible").

---

## 2. Gaps Necesarios para el MVP

### GAP-01: Incorporación de Roles de Usuario en `users`
* **Campo propuesto:** `users.role VARCHAR(50) NOT NULL DEFAULT 'viewer'`
* **HU que lo requiere:** `HU-01` (Autenticación y RBAC visual).
* **Justificación:** Los actores humanos definidos (Analista GRC, CISO, Auditor externo, DevSecOps e Ingeniero/Admin) requieren interfaces diferenciadas. El auditor solo debe tener permisos de lectura; el DevSecOps debe ver triggers de ejecución; el CISO debe ver el resumen ejecutivo.
* **Restricción:** `[PROPUESTO] CHECK (role IN ('admin', 'grc_analyst', 'devsecops', 'ciso', 'auditor', 'viewer'))`.
* **Impacto en datos legacy:** Mínimo. Se ejecuta un `ALTER TABLE users ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'viewer'`.

---

### GAP-02: Desacoplamiento de Unicidad en `evidence_records` (Alternativa B: Sin Deduplicar)
*(Estado: **Pendiente de confirmar con Jonathann**)*
* **Tabla afectada:** `evidence_records`.
* **Justificación Técnica:**
  1. El hash canónico SHA-256 cubre **exclusivamente los campos normalizados** (`control`, `dismiss_stale_reviews`, `required_review_approvals` en GH-001; `control`, `default_branch`, `protection_enabled` en GH-002). **No identifica el repositorio, la rama ni la estampa temporal (`collected_at`)**.
  2. Dos repositorios distintos con configuraciones idénticas generan exactamente el mismo hash.
  3. `evaluate_and_store_*` genera un `uuid4()` para `evidence_id` e inserta incondicionalmente en cada evaluación. Bajo el constraint `UNIQUE (control_id, evidence_hash, tenant_id)`, la segunda evaluación aborta con `IntegrityError`.
* **Decisión Adoptada (Alternativa B):**
  * Eliminar la restricción de unicidad para permitir que cada evaluación conserve su propio registro de evidencia y su fecha real de recolección (`collected_at`), garantizando la veracidad temporal requerida por la **HU-06**.
* **Migración Propuesta:**
  ```sql
  -- Soltar índice único
  DROP INDEX IF EXISTS uq_evidence_control_hash;
  -- Dejar índice B-tree no único para búsquedas de verificación de integridad por hash
  CREATE INDEX idx_evidence_control_hash ON evidence_records (control_id, evidence_hash);
  ```
* **Impacto en el Código:**
  * **En `src/securecode/adapters/postgres/models.py`:** En `EvidenceRecord.__table_args__`, modificar `Index('uq_evidence_control_hash', ..., unique=True)` a `Index('idx_evidence_control_hash', 'control_id', 'evidence_hash')` (sin `unique=True`).
  * **En Test 3 de TASK-05 (`database-schema` / `tests/integration/test_migrations.py`):** El test `test_unique_evidence_hash_per_tenant` esperaba un `IntegrityError` al duplicar. Con la Alternativa B, **dicho test debe actualizarse** para certificar que la inserción de múltiples evidencias con el mismo hash es permitida y válida.

---

### GAP-03: Causa de Estado `UNKNOWN` con Vocabulario Cerrado y CHECK Relajado
* **Campo propuesto:** `evaluation_records.unknown_reason VARCHAR(100) NULL`
* **HU que lo requiere:** `HU-07` (Diagnóstico de Estado UNKNOWN).
* **Vocabulario Cerrado (con `INCOMPLETE_EVIDENCE`):**
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
* **CHECK de Coherencia Relajado:**
  ```sql
  CONSTRAINT chk_eval_unknown_reason_coherence CHECK (
      status = 'UNKNOWN' OR unknown_reason IS NULL
  )
  ```
* **Por qué la versión bidireccional rompía datos legacy y endpoints:**
  - *Datos Legacy:* Todos los registros existentes en `evaluation_records` con `status = 'UNKNOWN'` poseen `unknown_reason IS NULL`. Una condición bidireccional (`status = 'UNKNOWN' AND unknown_reason IS NOT NULL`) habría violado de inmediato la integridad de los datos históricos.
  - *Endpoints Actuales:* [`app.py`](file:///c:/Users/achej/Documents/SecureCode/src/securecode/api/app.py) ejecuta `evaluate_and_store_*`, funciones que actualmente no inyectan `unknown_reason`. Si la regla forzara un valor no nulo, los endpoints fallarían con `IntegrityError` en producción ante cualquier evaluación en `UNKNOWN`.
  - *Comportamiento Relajado:* Impide que un `PASS` o `FAIL` tenga motivo de `UNKNOWN`, permitiendo `NULL` en `UNKNOWN` para compatibilidad regresiva.

---

### GAP-04: [ELIMINADO DEL ESQUEMA] Guía de Remediación Técnica ante `FAIL`
* **Estado:** **DESESTIMADO DE BASE DE DATOS — DELEGADO AL FRONTEND**
* **HU que lo requiere:** `HU-08`.
* **Justificación de la Decisión:** Se determinó que los pasos instructivos y enlaces profundos a GitHub Settings se mantendrán en la capa de frontend (archivos estáticos / componentes UI). Esto evita contaminar el esquema relacional y elimina la necesidad de migraciones ante ajustes de redacción.

---

### GAP-05: Relación Dual entre Evaluaciones y Fuentes (`source_id` + Texto Histórico)
* **Campo propuesto:** `evaluation_records.source_id UUID NULL REFERENCES sources(id) ON DELETE SET NULL`
* **HU que lo requiere:** `HU-09` (Fuentes conectadas y trazabilidad).
* **Justificación:** Se vincula relacionalmente la evaluación con `sources.id`, al mismo tiempo que se **preservan intactas `source_repository VARCHAR(255)` y `source_branch VARCHAR(255)`** como garantía de auditoría forense inalterable ante renombrados o bajas de repositorios.

---

### GAP-06: Migración de Siembra de Datos Iniciales (Seed Migration de `controls` y `rules`)
* **Tablas afectadas:** `controls`, `rules`.
* **Justificación:** La migración `ae4b780826f2` creó las tablas maestras `controls` y `rules`, pero están vacías por defecto. El motor de evaluación y el catálogo del frontend requieren que los controles base `GH-001` ("Branch Protection Review Rules") y `GH-002` ("Default Branch Protection Enabled"), junto con sus reglas canónicas activas `GH-001-RULE` y `GH-002-RULE` (versión 1, extraídas de `rules/GH-001.json` y `rules/GH-002.json`), se encuentren formalmente sembrados en PostgreSQL.
* **Propuesta:** Crear una migración de datos en Alembic (`seed_controls_and_rules`) que inserte de forma idempotente (`ON CONFLICT DO NOTHING`) los controles y sus reglas asociadas.

---

### GAP-07: Restricción para una Única Regla Activa por `rule_id`
* **Tabla afectada:** `rules`.
* **Justificación:** Un control puede relacionarse con su regla correspondiente (ej. control `GH-001` con regla `GH-001-RULE`, y `GH-002` con `GH-002-RULE`, o futuras reglas concurrentes), por lo que restringir por `(control_id)` limitaría la evolución del catálogo. Sin embargo, para un identificador de regla dado (`rule_id`), **no deben existir dos versiones marcadas con `active = TRUE` al mismo tiempo**.
* **Solución Propuesta para el MVP:** Crear un índice único parcial ajustado estrictamente a `(rule_id)`:
  ```sql
  CREATE UNIQUE INDEX uq_rules_one_active_per_rule 
  ON rules (rule_id) 
  WHERE active = TRUE;
  ```

---

## 3. Estado de la HU-06 y Precisiones Técnicas sobre `raw_evidence`

### HU-06 (Visor de JSON Crudo de GitHub) — NO SATISFECHA con el Esquema Actual
* **Hallazgo en Código:** En [`src/securecode/adapters/postgres/repository.py`](file:///c:/Users/achej/Documents/SecureCode/src/securecode/adapters/postgres/repository.py) (líneas 37–40 y 88–91), la columna `raw_evidence` **no almacena el payload crudo HTTP devuelto por la API de GitHub**, sino un diccionario con los **campos normalizados ya extraídos** (`required_review_approvals`, `dismiss_stale_reviews` en GH-001; `default_branch`, `protection_enabled` en GH-002).
* **Diagnóstico de Cumplimiento:** La HU-06 en su Escenario 2 (inspección del JSON crudo retornado por GitHub) se encuentra **NO SATISFECHA** con el esquema actual de base de datos.
* **Opciones de Resolución:**
  * **Opción 1 (Recomendada para MVP):** Reescribir el Escenario 2 de la HU-06 para que el visor presente la **evidencia normalizada** en formato JSON (que es exactamente lo que almacena `raw_evidence`). Esto satisface la necesidad de auditoría de los datos que alimentaron el motor de reglas sin requerir modificaciones en los adaptadores ni arriesgar filtración de credenciales.
  * **Opción 2 (Evolución Futura):** Persistir el **payload HTTP original devuelto por GitHub** (agregando por ejemplo una columna `github_http_payload` en `evidence_records`). Esta opción requiere:
    1. Modificar los adaptadores de GitHub (`github_adapter.py`) para capturar y propagar la respuesta HTTP cruda antes del filtrado.
    2. Realizar una exhaustiva revisión de la **política de cero secretos**, asegurando que no se persistan tokens, cabeceras de autorización, URLs con credenciales embebidas ni metadatos sensibles no relacionados en la base de datos.

---

## 4. Decisiones de Diseño Pendientes (Human Review Required)

### Decisión Pendiente 1: Severidad por Control (`controls.severity`)
* **Situación:** HU-03 requiere mostrar la severidad (`HIGH`, `MEDIUM`, `LOW`) en el catálogo de controles.
* **Alternativas:**
  * **Alternativa A (Columna en `controls`):** Agregar `severity VARCHAR(20) NOT NULL` (sin DEFAULT) mediante procedimiento de migración en tres pasos:
    1. *Paso 1 (Agregar nulo):* `ALTER TABLE controls ADD COLUMN severity VARCHAR(20) NULL;`
    2. *Paso 2 (UPDATE):* `UPDATE controls SET severity = 'HIGH' WHERE control_id IN ('GH-001', 'GH-002');`
    3. *Paso 3 (Fijar NOT NULL):* `ALTER TABLE controls ALTER COLUMN severity SET NOT NULL;` + `ADD CONSTRAINT chk_controls_severity CHECK (severity IN ('HIGH', 'MEDIUM', 'LOW'));`
  * **Alternativa B (Definida en Catálogo Frontend):** Mantener la severidad como metadato estático en el frontend/CMS, evitando migraciones de esquema en PostgreSQL.
  * **Alternativa C (Configurable por Tenant):** Permitir que cada organización defina el nivel de criticidad de cada control en fases futuras de multi-tenancy.

---

### Decisión Pendiente 2: Clave Foránea Compuesta de `evaluation_records` hacia `rules`
* **Situación:** `evaluation_records` almacena `rule_id VARCHAR(100)` y `rule_version INTEGER`, mientras que `rules` tiene `UNIQUE(rule_id, version)`. No existe FK relacional entre ambas.
* **Alternativas:**
  * **Alternativa A (FK Compuesta Formal):**
    ```sql
    ALTER TABLE evaluation_records 
    ADD CONSTRAINT fk_eval_rules 
    FOREIGN KEY (rule_id, rule_version) REFERENCES rules(rule_id, version) 
    ON UPDATE CASCADE ON DELETE RESTRICT;
    ```
    - *Ventaja:* Garantía de integridad matemática referencial.
    - *Desventaja:* Exige que toda regla histórica exista previamente en `rules` antes de poder insertar o migrar evaluaciones.
  * **Alternativa B (Mantener Desacoplado sin FK):**
    - *Ventaja:* Mantiene la auditoría forense de evaluaciones como bitácora independiente desvinculada de modificaciones de catálogo.
    - *Desventaja:* No previene inconsistencias tipográficas en `rule_id`.

---

## 5. Brechas de Evolución Futura (Post-MVP)

1. **Aislamiento Multi-Tenant Estricto:** Entidad `tenants`, `tenant_id NOT NULL` y PostgreSQL Row-Level Security (RLS).
2. **Sistema de Excepciones y Dispensas Temporales (Waivers):** Tabla `compliance_exceptions` vinculada a `evaluation_records` para autorizar `FAIL` temporales justificados.
3. **Mapeo Relacional N:M de Frameworks Regulatorios:** Tablas `compliance_frameworks` y `control_framework_mappings` (referencia a NIST CSF `PR.IP-1`: **pendiente de verificar contra NIST CSWP.29**).
4. **Historial de Invocaciones de Webhooks:** Tabla `webhook_deliveries` para auditoría de eventos de GitHub.

---

STOP.
