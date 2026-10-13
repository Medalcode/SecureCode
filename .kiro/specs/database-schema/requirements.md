# database-schema — Requirements

**Spec:** `database-schema`  
**Fecha:** 2026-10-07  
**Protocolo:** SDD (Audit → Evidence → Decision → Specification)

---

## 1. AUDIT — Estado del Repositorio

### 1.1 Lo que ya existe (IMPLEMENTED)

#### Tablas activas en PostgreSQL (via Alembic migrations)

| Tabla | Definida en | Estado |
|---|---|---|
| `evidence_records` | `7409c81f5bf7_baseline.py` | IMPLEMENTED |
| `evaluation_records` | `7409c81f5bf7_baseline.py` | IMPLEMENTED |
| `users` | `1bfdcaee6d14_auth.py` | IMPLEMENTED |

#### Columnas por tabla — estado actual

**`evidence_records`**
| Columna | Tipo | Constraints | Estado |
|---|---|---|---|
| `id` | UUID | PK | ✅ |
| `control_id` | VARCHAR(50) | NOT NULL | ✅ |
| `evidence_hash` | VARCHAR(64) | NOT NULL | ✅ SHA-256 hex |
| `raw_evidence` | JSONB | NOT NULL | ✅ payload original |
| `collected_at` | TIMESTAMPTZ | NOT NULL | ✅ |

**`evaluation_records`**
| Columna | Tipo | Constraints | Estado |
|---|---|---|---|
| `id` | UUID | PK | ✅ |
| `control_id` | VARCHAR(50) | NOT NULL | ✅ |
| `rule_id` | VARCHAR(100) | NULL | ✅ migración 4d93… |
| `rule_version` | INTEGER | NULL | ✅ migración 4d93… |
| `status` | VARCHAR(50) | NOT NULL | ✅ PASS/FAIL/UNKNOWN |
| `evaluated_at` | TIMESTAMPTZ | NOT NULL | ✅ |
| `evidence_id` | UUID | FK → evidence_records.id | ✅ |
| `requested_by_user_id` | UUID | FK → users.id, NULL | ✅ migración 1bfd… |
| `source_type` | VARCHAR(50) | NOT NULL | ✅ literal "GitHub" |
| `source_repository` | VARCHAR(255) | NOT NULL | ✅ "owner/repo" |
| `source_branch` | VARCHAR(255) | NOT NULL | ✅ |

**`users`**
| Columna | Tipo | Constraints | Estado |
|---|---|---|---|
| `id` | UUID | PK | ✅ |
| `username` | VARCHAR(100) | UNIQUE, NOT NULL | ✅ |
| `password_hash` | VARCHAR(255) | NOT NULL | ✅ bcrypt |
| `active` | BOOLEAN | NOT NULL, DEFAULT true | ✅ |
| `created_at` | TIMESTAMPTZ | NOT NULL | ✅ |

#### Infraestructura de migraciones
- Alembic configurado (`alembic.ini` + `alembic/env.py`).
- Cadena de migraciones: `baseline (7409) → rule_traceability (4d93) → auth (1bfd)`.
- `alembic/env.py` enlaza con `Base.metadata` del ORM SQLAlchemy.
- SQLite como fallback offline (`securecode.db` en raíz).
- Tests de migración en `tests/integration/test_migrations.py` (fresh install, historical preservation, schema parity, new evaluations post-migration).

#### Modelos de dominio (Python)
- `GH001Evidence` — dataclass frozen, hash SHA-256 canónico con `control: "GH-001"`.
- `GH002Evidence` — dataclass frozen, hash SHA-256 canónico con `control: "GH-002"`.
- `RuleDefinition` / `ControlDefinition` / `Condition` / `AndCondition` — Pydantic, en memoria, **no persistidos en BD**.
- `EvaluationRecord` + `EvidenceRecord` + `User` — SQLAlchemy ORM mapeados a las tablas.

#### Port / Adaptador
- `EvaluationRepository` (Protocol) con `save_gh001_evaluation`, `save_gh002_evaluation`, `get_evaluation`.
- `PostgresEvaluationRepository` implementa el port.
- Operaciones atómicas: evidence + evaluation se insertan en la misma transacción.

---

### 1.2 Lo que FALTA (GAPs identificados)

#### GAP-1: No hay tabla `controls`
El flujo GRC comienza con **definir el control**. Hoy `control_id` es un string libre (`"GH-001"`, `"GH-002"`) sin tabla maestra que lo valide ni almacene metadatos (nombre, descripción, fuente, activo/inactivo). `ControlDefinition` existe en Pydantic pero nunca se persiste.

#### GAP-2: No hay tabla `rules`
`RuleDefinition` existe en Pydantic y en archivos JSON en `rules/`. No hay tabla que registre las reglas históricas, sus versiones, condiciones ni qué control gobiernan. Hoy `rule_id` y `rule_version` en `evaluation_records` son nullable porque la regla no se puede referenciar por FK.

#### GAP-3: No hay tabla `sources` (conexiones de fuente)
El flujo requiere **conectar fuente (GitHub)**. Hoy `source_type`, `source_repository`, `source_branch` son strings planos inlined en cada `evaluation_record`. No hay entidad que modele la conexión reutilizable (token, owner, repo, estado de la conexión).

#### GAP-4: Sin índices declarados en migraciones
No hay `op.create_index(...)` en ninguna migración. Las consultas por `control_id`, `status`, `evaluated_at`, `source_repository` y `evidence_hash` carecen de índices explícitos, impactando performance en volumen.

#### GAP-5: Sin constraint `UNIQUE` en `evidence_hash`
El hash SHA-256 de evidencia debe ser único por `(control_id, evidence_hash)` para garantizar inmutabilidad y detectar duplicados. No existe este constraint.

#### GAP-6: Sin campo `tenant_id` / multi-tenancy
El README menciona "Multi-Tenancy" como siguiente fase planificada. Ninguna tabla tiene columna de tenant. Agregar esto después de tener datos es una migración costosa.

#### GAP-7: Sin tabla de reporte / `report_snapshots`
El flujo termina en **consultar reporte**. No hay tabla que materialice el estado de un conjunto de controles en un punto en el tiempo (snapshot de compliance). Hoy solo se puede reconstruir desde `evaluation_records` con lógica de aplicación.

#### GAP-8: Sin FK explícita nombrada entre `evaluation_records.control_id` y tabla de controles
Actualmente `control_id` es un string sin referencia de integridad. Si se crea `controls`, la migración debe agregar la FK.

---

## 2. EVIDENCE — Clasificación de Hallazgos

| ID | Hallazgo | Clasificación |
|---|---|---|
| E-01 | Tablas `evidence_records`, `evaluation_records`, `users` con Alembic | IMPLEMENTED |
| E-02 | Hash SHA-256 canónico en modelos Python | IMPLEMENTED |
| E-03 | ORM SQLAlchemy con relaciones ORM | IMPLEMENTED |
| E-04 | Port `EvaluationRepository` + impl Postgres | IMPLEMENTED |
| E-05 | Cadena Alembic funcional con 3 migraciones | IMPLEMENTED |
| E-06 | Tests de migración (fresh, histórico, paridad, post-migración) | IMPLEMENTED |
| E-07 | Tabla `controls` persisted | FALTANTE |
| E-08 | Tabla `rules` persisted | FALTANTE |
| E-09 | Tabla `sources` (conexiones reutilizables) | FALTANTE |
| E-10 | Índices en columnas de consulta frecuente | FALTANTE |
| E-11 | UNIQUE constraint `(control_id, evidence_hash)` | FALTANTE |
| E-12 | Soporte multi-tenancy (`tenant_id`) | PLANIFICADO |
| E-13 | Tabla `report_snapshots` | PLANIFICADO |

---

## 3. DECISION — Qué problema resuelve este spec

**Problema:** El esquema actual modela correctamente el caso de uso del primer slice (evaluar + persistir un control GH-001/GH-002), pero no soporta el flujo GRC completo: definir controles y reglas como entidades persistidas, registrar fuentes conectadas, ni consultar reportes de compliance por repositorio.

**Decisión:** Especificar el esquema PostgreSQL completo para el dominio GRC, incluyendo:
1. Las tablas ya implementadas como base (no se reescriben, se extienden con índices y constraints faltantes).
2. Las tablas faltantes para el flujo completo: `controls`, `rules`, `sources`.
3. Indexado explícito para las columnas de consulta más frecuentes.
4. UNIQUE constraint en evidencia para garantizar inmutabilidad.
5. Dejar `tenant_id` como columna nullable en todas las tablas nuevas (preparación sin ruptura).
6. **Fuera de scope:** `report_snapshots` (requiere spec de reporting separado), cambios al flujo de auth.

---

## 4. SPECIFICATION — Requisitos del Esquema

### REQ-DB-001: Tabla `controls`

**Propósito:** Catálogo maestro de controles GRC. Actualmente `ControlDefinition` existe solo en memoria.

```sql
CREATE TABLE controls (
    id          UUID PRIMARY KEY,
    control_id  VARCHAR(50) NOT NULL UNIQUE,   -- "GH-001", "GH-002"
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    source_type VARCHAR(50) NOT NULL DEFAULT 'GitHub',
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    tenant_id   UUID NULL                       -- preparación multi-tenancy
);
CREATE INDEX idx_controls_control_id  ON controls(control_id);
CREATE INDEX idx_controls_source_type ON controls(source_type);
```

**Criterios de aceptación:**
- `control_id` es UNIQUE; INSERT de duplicado debe fallar con violación de constraint.
- `active = FALSE` marca un control como deshabilitado sin eliminar histórico.
- `tenant_id` NULL significa control global (compartido por todos los tenants).

---

### REQ-DB-002: Tabla `rules`

**Propósito:** Persistir versiones históricas de `RuleDefinition`. Hoy solo existen como archivos JSON. Permite auditoría de cambios de regla.

```sql
CREATE TABLE rules (
    id          UUID PRIMARY KEY,
    rule_id     VARCHAR(100) NOT NULL,
    control_id  VARCHAR(50) NOT NULL REFERENCES controls(control_id),
    version     INTEGER NOT NULL,
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    condition   JSONB NOT NULL,                -- condición serializada
    allowlisted_fields JSONB NOT NULL,         -- lista de campos permitidos
    created_at  TIMESTAMPTZ NOT NULL,
    tenant_id   UUID NULL,
    UNIQUE (rule_id, version)
);
CREATE INDEX idx_rules_control_id ON rules(control_id);
CREATE INDEX idx_rules_rule_id    ON rules(rule_id);
CREATE INDEX idx_rules_active     ON rules(active);
```

**Criterios de aceptación:**
- `(rule_id, version)` es UNIQUE: no pueden existir dos registros con el mismo `rule_id` y `version`.
- `active = FALSE` permite desactivar una versión de regla sin borrarla.
- `condition` almacena el JSON canónico de la condición (mismo formato que `rules/GH-001.json`).
- FK a `controls(control_id)` garantiza integridad referencial con el catálogo.

---

### REQ-DB-003: Tabla `sources`

**Propósito:** Modelar conexiones reutilizables a fuentes de evidencia (repositorios GitHub). Actualmente inline como strings en `evaluation_records`.

```sql
CREATE TABLE sources (
    id               UUID PRIMARY KEY,
    source_type      VARCHAR(50) NOT NULL DEFAULT 'GitHub',
    owner            VARCHAR(255) NOT NULL,
    repository       VARCHAR(255) NOT NULL,
    default_branch   VARCHAR(255) NOT NULL DEFAULT 'main',
    active           BOOLEAN NOT NULL DEFAULT TRUE,
    connected_at     TIMESTAMPTZ NOT NULL,
    last_checked_at  TIMESTAMPTZ NULL,
    tenant_id        UUID NULL,
    UNIQUE (source_type, owner, repository, tenant_id)
);
CREATE INDEX idx_sources_owner_repo ON sources(owner, repository);
CREATE INDEX idx_sources_source_type ON sources(source_type);
```

**Criterios de aceptación:**
- `(source_type, owner, repository, tenant_id)` UNIQUE para evitar fuentes duplicadas.
- `last_checked_at` se actualiza en cada ejecución de evidencia.
- `active = FALSE` desconecta la fuente sin eliminar evaluaciones históricas.

---

### REQ-DB-004: Índices en tablas existentes

**Propósito:** Las tablas actuales carecen de índices; su ausencia es un gap productivo.

```sql
-- evidence_records
CREATE UNIQUE INDEX idx_evidence_hash_unique
    ON evidence_records(control_id, evidence_hash);

CREATE INDEX idx_evidence_control_id  ON evidence_records(control_id);
CREATE INDEX idx_evidence_collected_at ON evidence_records(collected_at);

-- evaluation_records
CREATE INDEX idx_eval_control_id      ON evaluation_records(control_id);
CREATE INDEX idx_eval_status          ON evaluation_records(status);
CREATE INDEX idx_eval_evaluated_at    ON evaluation_records(evaluated_at);
CREATE INDEX idx_eval_source_repo     ON evaluation_records(source_repository);
CREATE INDEX idx_eval_rule_id         ON evaluation_records(rule_id);
```

**Criterios de aceptación:**
- `UNIQUE INDEX (control_id, evidence_hash)` previene evidencia duplicada para el mismo control.
- Los índices en `evaluation_records` habilitan consultas de reporte por control, estado, fecha y repositorio.

---

### REQ-DB-005: Migración incremental Alembic

**Propósito:** Los cambios al esquema se entregan como una nueva migración, no como reescritura del baseline.

**Criterios de aceptación:**
- La migración se puede aplicar sobre una BD existente sin pérdida de datos (`upgrade`).
- `downgrade()` revierte los cambios en orden inverso.
- Los tests de migración existentes en `tests/integration/test_migrations.py` siguen pasando.
- Se agrega al menos un test que verifica la nueva cadena de migración aplicada a una BD vacía.

---

### REQ-DB-006: Constraint de integridad en `evaluation_records`

**Propósito:** `rule_id` y `rule_version` en `evaluation_records` deben poder referenciar `rules` una vez que esa tabla exista. Hoy son NULL para compatibilidad histórica.

**Criterios de aceptación:**
- Los registros históricos (sin `rule_id`) permanecen válidos (columna sigue siendo nullable).
- Los nuevos registros con `rule_id` NO NULL + `rule_version` NO NULL deben pasar validación a nivel de aplicación (no FK en esta migración, para evitar romper datos legacy).
- Se documenta en código que la FK completa es trabajo futuro cuando se migre el histórico.

---

### REQ-DB-007: Preparación multi-tenancy (no-op inicial)

**Propósito:** Incluir `tenant_id UUID NULL` en las tablas nuevas (`controls`, `rules`, `sources`) para evitar una migración costosa posterior.

**Criterios de aceptación:**
- `tenant_id` es NULL en todas las tablas nuevas por defecto.
- No se agrega `tenant_id` a las tablas existentes (`evidence_records`, `evaluation_records`, `users`) en este spec; eso pertenece a un spec de multi-tenancy dedicado.
- La lógica de aplicación ignora `tenant_id` hasta que el spec de multi-tenancy lo active.

---

## 5. Diagrama de Relaciones — Estado Objetivo

```
controls (REQ-DB-001)
  ├── control_id (UNIQUE)
  └── ← rules.control_id (REQ-DB-002)

rules (REQ-DB-002)
  ├── (rule_id, version) UNIQUE
  └── → controls.control_id

sources (REQ-DB-003)
  └── (source_type, owner, repository, tenant_id) UNIQUE

evidence_records (existente + REQ-DB-004)
  ├── UNIQUE INDEX (control_id, evidence_hash)
  └── ← evaluation_records.evidence_id

evaluation_records (existente + REQ-DB-004)
  ├── → evidence_records.id
  ├── → users.id (requested_by_user_id, nullable)
  ├── rule_id / rule_version (nullable, lógica en app)
  └── source_repository / source_branch (strings, future FK a sources)

users (existente)
```

---

## 6. Fuera de Scope (este spec)

- **`report_snapshots`** — requiere spec de reporting / compliance dashboard.
- **FK `evaluation_records.rule_id` → `rules`** — requiere migración de datos históricos; spec separado.
- **FK `evaluation_records.source_repository` → `sources`** — ídem.
- **Activación de `tenant_id`** — spec de multi-tenancy.
- **Cambios a autenticación / `users`** — spec de auth.
