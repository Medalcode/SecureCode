# database-schema — Design

**Spec:** `database-schema`  
**Fecha:** 2026-10-07  
**Depende de:** `requirements.md` (REQ-DB-001 a REQ-DB-007)

---

## 1. Diagrama ER — Estado Objetivo

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                         SecureCode — Esquema PostgreSQL                              │
│                         (estado objetivo post-migración)                             │
└──────────────────────────────────────────────────────────────────────────────────────┘

 ┌─────────────┐       ┌──────────────────────────────────────────┐
 │   controls  │       │              evidence_records            │
 ├─────────────┤       ├──────────────────────────────────────────┤
 │ id (PK)     │       │ id (PK)                                  │
 │ control_id  │◄──┐   │ control_id ──────────────────────────────┼──► (string, no FK aún)
 │ name        │   │   │ evidence_hash                            │
 │ description │   │   │ raw_evidence (JSONB)                     │
 │ source_type │   │   │ collected_at (TIMESTAMPTZ)               │
 │ active      │   │   │ tenant_id (UUID, NULL) ← NUEVO           │
 │ created_at  │   │   └──────────────────────────────────────────┘
 │ updated_at  │   │                    │ 1
 │ tenant_id ← NUEVO   │                    │
 └─────────────┘   │                    │ N
       │ 1         │   ┌──────────────────────────────────────────┐
       │           │   │           evaluation_records             │
       │ N         │   ├──────────────────────────────────────────┤
       ▼           │   │ id (PK)                                  │
 ┌──────────────┐  │   │ control_id ──────────────────────────────┼──► (string, no FK aún)
 │    rules     │  │   │ rule_id (NULL)                           │
 ├──────────────┤  │   │ rule_version (NULL)                      │
 │ id (PK)      │  └───┼─ evidence_id (FK → evidence_records.id) │
 │ rule_id      │      │ status                                   │
 │ control_id ──┼──────┤ evaluated_at (TIMESTAMPTZ)               │
 │ version      │      │ source_type                              │
 │ active       │      │ source_repository                        │
 │ condition    │      │ source_branch                            │
 │ allowlisted  │      │ requested_by_user_id (FK → users.id, NULL│
 │ created_at   │      │ tenant_id (UUID, NULL) ← NUEVO           │
 │ tenant_id ← NUEVO   └──────────────────────────────────────────┘
 └──────────────┘
                              ┌──────────────────────────────────────┐
                              │               users                  │
 ┌──────────────────────┐     ├──────────────────────────────────────┤
 │       sources        │     │ id (PK)                              │
 ├──────────────────────┤     │ username (UNIQUE)                    │
 │ id (PK)              │     │ password_hash                        │
 │ source_type          │     │ active                               │
 │ owner                │     │ created_at                           │
 │ repository           │     └──────────────────────────────────────┘
 │ default_branch       │       ↑ FK desde evaluation_records
 │ active               │         (requested_by_user_id)
 │ connected_at         │
 │ last_checked_at (NULL│
 │ tenant_id ← NUEVO    │
 └──────────────────────┘

 Leyenda:
   ← NUEVO   columna nueva que no existe en el estado actual
   ─────►    referencia lógica (string), FK formal es trabajo futuro
   FK        referencia formal con FOREIGN KEY constraint activo
```

---

## 2. DDL Completo — Tablas Nuevas

### 2.1 `controls`

```sql
-- ===========================================================================
-- Tabla: controls
-- Propósito: Catálogo maestro de controles GRC.
--            Persiste lo que hoy solo existe en ControlDefinition (Pydantic).
-- ===========================================================================
CREATE TABLE controls (
    id           UUID         NOT NULL DEFAULT gen_random_uuid(),
    control_id   VARCHAR(50)  NOT NULL,          -- "GH-001", "GH-002", etc.
    name         VARCHAR(200) NOT NULL,
    description  TEXT,
    source_type  VARCHAR(50)  NOT NULL DEFAULT 'GitHub',
    active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    tenant_id    UUID                  DEFAULT NULL,  -- NULL = control global
    CONSTRAINT pk_controls PRIMARY KEY (id),
    CONSTRAINT uq_controls_control_id UNIQUE (control_id)
);

-- Índices
CREATE INDEX idx_controls_control_id  ON controls (control_id);
CREATE INDEX idx_controls_source_type ON controls (source_type);
CREATE INDEX idx_controls_active      ON controls (active);
CREATE INDEX idx_controls_tenant_id   ON controls (tenant_id);  -- multi-tenancy prep
```

**Notas de diseño:**
- `control_id` es UNIQUE globalmente (sin incluir `tenant_id`) porque los identificadores como `"GH-001"` son referencias externas fijas del estándar GRC.
- `DEFAULT gen_random_uuid()` elimina la necesidad de generar UUID en la capa de aplicación, pero la aplicación puede seguir pasando su propio UUID.
- `updated_at` debe actualizarse vía trigger o desde la capa de aplicación; no se define trigger en este DDL para mantener compatibilidad con el patrón Alembic actual.

---

### 2.2 `rules`

```sql
-- ===========================================================================
-- Tabla: rules
-- Propósito: Historial versionado de RuleDefinition.
--            Persiste lo que hoy solo existe en rules/GH-001.json, GH-002.json.
--            Permite auditoría de cambios de regla y FK desde evaluations.
-- ===========================================================================
CREATE TABLE rules (
    id                 UUID         NOT NULL DEFAULT gen_random_uuid(),
    rule_id            VARCHAR(100) NOT NULL,   -- "GH-001-RULE", "GH-002-RULE"
    control_id         VARCHAR(50)  NOT NULL,   -- FK → controls.control_id
    version            INTEGER      NOT NULL,
    active             BOOLEAN      NOT NULL DEFAULT TRUE,
    condition          JSONB        NOT NULL,   -- condición serializada (objeto JSON)
    allowlisted_fields JSONB        NOT NULL,   -- ["required_review_approvals", ...]
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    tenant_id          UUID                  DEFAULT NULL,
    CONSTRAINT pk_rules PRIMARY KEY (id),
    CONSTRAINT uq_rules_rule_version UNIQUE (rule_id, version),
    CONSTRAINT fk_rules_control_id
        FOREIGN KEY (control_id)
        REFERENCES controls (control_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- Índices
CREATE INDEX idx_rules_control_id ON rules (control_id);
CREATE INDEX idx_rules_rule_id    ON rules (rule_id);
CREATE INDEX idx_rules_active     ON rules (active);
CREATE INDEX idx_rules_tenant_id  ON rules (tenant_id);  -- multi-tenancy prep
```

**Notas de diseño:**
- `(rule_id, version)` UNIQUE: no existen dos versiones iguales para la misma regla.
- `condition` almacena el JSON exacto tal como aparece en `rules/GH-001.json`. Ejemplo:
  ```json
  {"operator":"AND","conditions":[
    {"field":"required_review_approvals","operator":"GTE","value":2},
    {"field":"dismiss_stale_reviews","operator":"EQ","value":true}
  ]}
  ```
- `allowlisted_fields` almacena el array JSON: `["required_review_approvals","dismiss_stale_reviews"]`.
- FK `ON UPDATE CASCADE`: si cambia el `control_id` en `controls` (raro pero posible en renaming), se propaga.
- FK `ON DELETE RESTRICT`: intencional. El flujo correcto para retirar un control es `UPDATE controls SET active = FALSE` (soft-delete), nunca `DELETE`. `RESTRICT` actúa como seguro de red a nivel BD: si alguien intenta un `DELETE` directo (desde SQL, migración, o herramienta externa), PostgreSQL lo rechaza con error explícito en lugar de propagar silenciosamente la eliminación a las reglas y dejar huérfanos los `rule_id`/`rule_version` en `evaluation_records` históricos. `CASCADE` fue descartado porque rompería la cadena de trazabilidad de evaluaciones pasadas de forma irreversible.
- No se agrega FK desde `evaluation_records.rule_id` → `rules.rule_id` en esta migración; los registros históricos tienen `rule_id` nullable y migrar ese FK rompería datos existentes. Esto es trabajo futuro.

---

### 2.3 `sources`

```sql
-- ===========================================================================
-- Tabla: sources
-- Propósito: Conexiones reutilizables a fuentes de evidencia.
--            Modela el paso "conectar fuente (GitHub)" del flujo GRC.
--            Hoy source_type/repository/branch son strings inline en evaluations.
-- ===========================================================================
CREATE TABLE sources (
    id               UUID         NOT NULL DEFAULT gen_random_uuid(),
    source_type      VARCHAR(50)  NOT NULL DEFAULT 'GitHub',
    owner            VARCHAR(255) NOT NULL,    -- "Medalcode"
    repository       VARCHAR(255) NOT NULL,    -- "securecode"
    default_branch   VARCHAR(255) NOT NULL DEFAULT 'main',
    active           BOOLEAN      NOT NULL DEFAULT TRUE,
    connected_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_checked_at  TIMESTAMPTZ           DEFAULT NULL,
    tenant_id        UUID                  DEFAULT NULL,
    CONSTRAINT pk_sources PRIMARY KEY (id),
    CONSTRAINT uq_sources_repo_tenant
        UNIQUE (source_type, owner, repository, tenant_id)
);

-- Índices
CREATE INDEX idx_sources_owner_repo   ON sources (owner, repository);
CREATE INDEX idx_sources_source_type  ON sources (source_type);
CREATE INDEX idx_sources_active       ON sources (active);
CREATE INDEX idx_sources_tenant_id    ON sources (tenant_id);  -- multi-tenancy prep
```

**Notas de diseño:**
- UNIQUE incluye `tenant_id` para que en multi-tenancy distintos tenants puedan tener la misma fuente (repo público evaluado por múltiples organizaciones).
- `last_checked_at` se actualiza cada vez que se ejecuta `evaluate_and_store_*`; no es NOT NULL porque una fuente recién conectada aún no ha sido evaluada.
- El campo `owner` + `repository` replica la lógica actual de `f"{owner}/{repo}"` en `source_repository` de `evaluation_records`. La FK formal entre `evaluation_records.source_repository` y `sources` es trabajo futuro (requiere migrar datos históricos).

---

## 3. DDL — Modificaciones a Tablas Existentes

### 3.1 Índices faltantes en `evidence_records`

```sql
-- ===========================================================================
-- Índices: evidence_records
-- Tablas existente — sin índices en ninguna migración previa.
-- ===========================================================================

-- UNIQUE: previene insertar evidencia duplicada para el mismo control dentro de un tenant.
-- Incluye tenant_id por la misma razón que sources: dos tenants distintos pueden evaluar
-- el mismo repositorio público y obtener evidencia idéntica (mismo hash). Sin tenant_id
-- en el UNIQUE, la segunda inserción fallaría aunque sean organizaciones distintas.
-- Comportamiento con NULL: PostgreSQL trata dos NULLs como distintos en UNIQUE B-tree,
-- por lo que los registros globales (tenant_id NULL) no colisionan entre sí — esto
-- preserva compatibilidad con todos los datos existentes sin necesidad de backfill.
CREATE UNIQUE INDEX uq_evidence_control_hash
    ON evidence_records (control_id, evidence_hash, tenant_id);

-- Índice para búsquedas frecuentes por control
CREATE INDEX idx_evidence_control_id   ON evidence_records (control_id);

-- Índice para rango de fechas (reportes, auditoría)
CREATE INDEX idx_evidence_collected_at ON evidence_records (collected_at);

-- Índice multi-tenancy (preparación — columna se agrega en sección 3.3)
CREATE INDEX idx_evidence_tenant_id    ON evidence_records (tenant_id);
```

---

### 3.2 Índices faltantes en `evaluation_records`

```sql
-- ===========================================================================
-- Índices: evaluation_records
-- Tabla existente — sin índices en ninguna migración previa.
-- ===========================================================================

-- Filtro por control (consultas de reporte más frecuentes)
CREATE INDEX idx_eval_control_id    ON evaluation_records (control_id);

-- Filtro por resultado (PASS / FAIL / UNKNOWN)
CREATE INDEX idx_eval_status        ON evaluation_records (status);

-- Rango de fechas para reportes de compliance
CREATE INDEX idx_eval_evaluated_at  ON evaluation_records (evaluated_at);

-- Consultas por repositorio (dashboard de fuente)
CREATE INDEX idx_eval_source_repo   ON evaluation_records (source_repository);

-- Trazabilidad de regla (join futuro con tabla rules)
CREATE INDEX idx_eval_rule_id       ON evaluation_records (rule_id);

-- Índice multi-tenancy (preparación — columna se agrega en sección 3.3)
CREATE INDEX idx_eval_tenant_id     ON evaluation_records (tenant_id);
```

---

### 3.3 Columna `tenant_id` en tablas existentes

```sql
-- ===========================================================================
-- ADD COLUMN tenant_id — evidence_records y evaluation_records
-- Decisión: agregar ahora para evitar migración costosa al activar multi-tenancy.
-- Ninguna lógica de aislamiento se activa; el campo es NULL para todos los
-- registros existentes y nuevos hasta que el spec de multi-tenancy lo active.
-- ===========================================================================

ALTER TABLE evidence_records
    ADD COLUMN tenant_id UUID DEFAULT NULL;

ALTER TABLE evaluation_records
    ADD COLUMN tenant_id UUID DEFAULT NULL;
```

**Justificación de agregar `tenant_id` a tablas existentes:**
- Una migración futura que agregue `tenant_id` a millones de filas y construya el índice en caliente puede generar lock de tabla durante minutos en producción.
- Agregarlo ahora (con `DEFAULT NULL`) es una operación O(1) en PostgreSQL moderno (no reescribe filas; solo actualiza el catálogo).
- El índice posterior sobre una columna mayormente NULL tiene un costo de storage mínimo en PostgreSQL (los NULLs no se indexan en B-tree salvo condiciones explícitas).
- El spec de multi-tenancy podrá simplemente activar el filtro sin necesitar `ALTER TABLE`.

---

## 4. Decisiones de Tipo

| Campo | Tipo elegido | Alternativas consideradas | Razón |
|---|---|---|---|
| `id` (todas las tablas) | `UUID` | SERIAL/BIGINT | Consistencia con el esquema existente; IDs seguros para APIs públicas |
| `condition` (rules) | `JSONB` | JSON, TEXT | JSONB permite consultas con operadores `@>`, `?` sin deserializar en app |
| `allowlisted_fields` (rules) | `JSONB` | TEXT[], VARCHAR[] | Consistencia con JSONB; permite `@>` para verificar campos |
| `raw_evidence` (existente) | `JSONB` | JSON | Ya implementado; JSONB tiene índices GIN disponibles |
| `control_id` (FK lógica) | `VARCHAR(50)` | UUID FK | `control_id` es un identificador de negocio legible; UUID FK requeriría JOIN siempre |
| `tenant_id` (todas) | `UUID NULL` | INTEGER FK, VARCHAR | UUID permite que el tenant ID sea un ID externo (Auth0, Keycloak) sin migración |
| Timestamps | `TIMESTAMPTZ` | `TIMESTAMP` | Timezone-aware; PostgreSQL almacena en UTC; consistente con el esquema existente |
| `source_type` | `VARCHAR(50)` | ENUM | VARCHAR permite agregar nuevos tipos de fuente (GitLab, Bitbucket) sin migración DDL |
| `status` (existente) | `VARCHAR(50)` | ENUM | Idem; `PASS`/`FAIL`/`UNKNOWN` puede extenderse sin `ALTER TYPE` |

---

## 5. Estrategia de Migración Alembic

La nueva migración debe ser la **4ta en la cadena**, apilada sobre `1bfdcaee6d14_auth`:

```
baseline (7409c81f5bf7)
    └─► rule_traceability (4d932f877ae7)
            └─► auth (1bfdcaee6d14)
                    └─► domain_schema (NUEVA — a implementar en tasks.md)
```

**Nombre sugerido del archivo:** `xxxx_domain_schema.py`  
**Descripción:** `"add controls, rules, sources tables + indices + tenant_id columns"`

La migración debe:
1. Crear `controls` (sin dependencias).
2. Crear `rules` (FK → `controls.control_id`).
3. Crear `sources` (sin dependencias de las anteriores).
4. Agregar `ADD COLUMN tenant_id` a `evidence_records`.
5. Agregar `ADD COLUMN tenant_id` a `evaluation_records`.
6. Crear todos los índices declarados en secciones 3.1 y 3.2 (incluidos los de `tenant_id`).
7. Crear los índices de las tablas nuevas (secciones 2.1, 2.2, 2.3).

**`downgrade()` debe revertir en orden inverso:**
1. Eliminar índices de tablas existentes.
2. `DROP COLUMN tenant_id` de `evaluation_records`.
3. `DROP COLUMN tenant_id` de `evidence_records`.
4. `DROP TABLE sources`.
5. `DROP TABLE rules`.
6. `DROP TABLE controls`.

---

## 6. Invariantes de Integridad

| Invariante | Mecanismo |
|---|---|
| `control_id` único por catálogo | `UNIQUE (control_id)` en `controls` |
| Una sola versión por `(rule_id, version)` | `UNIQUE (rule_id, version)` en `rules` |
| Evidencia no duplicada por control dentro de un tenant | `UNIQUE INDEX (control_id, evidence_hash, tenant_id)` en `evidence_records`; NULLs tratados como distintos por PostgreSQL → compatible con datos legacy |
| Una sola fuente por `(tipo, owner, repo, tenant)` | `UNIQUE (source_type, owner, repository, tenant_id)` en `sources` |
| No se elimina un control con reglas activas | `FK ON DELETE RESTRICT` en `rules.control_id` |
| `rule_id`/`rule_version` en evaluaciones puede ser NULL | Nullable columns — compatibilidad con registros legacy |

---

## 7. Lo que este diseño NO hace (fuera de scope)

- **No activa Row-Level Security (RLS)** para `tenant_id`; eso es del spec de multi-tenancy.
- **No agrega FK formal** `evaluation_records.rule_id → rules.rule_id`; requiere migración de datos legacy.
- **No agrega FK formal** `evaluation_records.source_repository → sources`; ídem.
- **No agrega `tenant_id` a `users`**; los usuarios son globales o del spec de multi-tenancy.
- **No crea triggers** para `updated_at`; la aplicación es responsable.
- **No crea índices GIN** sobre `raw_evidence` o `condition`; se pueden agregar si emergen consultas JSONB frecuentes.
