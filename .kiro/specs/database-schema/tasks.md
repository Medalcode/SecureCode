# database-schema — Tasks

**Spec:** `database-schema`  
**Fecha:** 2026-10-07  
**Depende de:** `requirements.md`, `design.md`  
**Protocolo SDD:** Minimal Implementation → Validation → STOP

---

## Criterios de Aceptación Globales

Antes de cerrar este spec, deben cumplirse todos los siguientes:

- [ ] `alembic upgrade head` ejecuta sin error sobre BD vacía
- [ ] `alembic upgrade head` ejecuta sin error sobre BD con datos del slice GH-001/GH-002 (datos legacy)
- [ ] `alembic downgrade base` revierte todo sin error
- [ ] Los 4 tests de migración existentes en `tests/integration/test_migrations.py` siguen pasando
- [ ] Los nuevos tests de migración (TASK-05) pasan
- [ ] El ORM SQLAlchemy (`adapters/postgres/models.py`) refleja las nuevas tablas y columnas
- [ ] `alembic check` no reporta diferencias entre modelos ORM y BD (schema parity)

---

## TASK-01 — Crear migración Alembic `domain_schema`

**Archivo:** `alembic/versions/<rev_id>_domain_schema.py`  
**`down_revision`:** `'1bfdcaee6d14'` (migración `auth`)  
**Descripción:** `"add controls, rules, sources tables + indices + tenant_id columns"`

### upgrade() — orden de ejecución

El orden importa: `rules` tiene FK hacia `controls`, así que `controls` debe existir primero.

**Paso 1 — Crear tabla `controls`**
```python
op.create_table(
    'controls',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('control_id', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('source_type', sa.String(length=50), nullable=False, server_default='GitHub'),
    sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('control_id', name='uq_controls_control_id'),
)
op.create_index('idx_controls_control_id',  'controls', ['control_id'])
op.create_index('idx_controls_source_type', 'controls', ['source_type'])
op.create_index('idx_controls_active',      'controls', ['active'])
op.create_index('idx_controls_tenant_id',   'controls', ['tenant_id'])
```

**Paso 2 — Crear tabla `rules`**
```python
op.create_table(
    'rules',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('rule_id', sa.String(length=100), nullable=False),
    sa.Column('control_id', sa.String(length=50), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
    sa.Column('condition', JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('allowlisted_fields', JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('rule_id', 'version', name='uq_rules_rule_version'),
    sa.ForeignKeyConstraint(
        ['control_id'], ['controls.control_id'],
        name='fk_rules_control_id',
        onupdate='CASCADE',
        ondelete='RESTRICT',
    ),
)
op.create_index('idx_rules_control_id', 'rules', ['control_id'])
op.create_index('idx_rules_rule_id',    'rules', ['rule_id'])
op.create_index('idx_rules_active',     'rules', ['active'])
op.create_index('idx_rules_tenant_id',  'rules', ['tenant_id'])
```

**Paso 3 — Crear tabla `sources`**
```python
op.create_table(
    'sources',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('source_type', sa.String(length=50), nullable=False, server_default='GitHub'),
    sa.Column('owner', sa.String(length=255), nullable=False),
    sa.Column('repository', sa.String(length=255), nullable=False),
    sa.Column('default_branch', sa.String(length=255), nullable=False, server_default='main'),
    sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
    sa.Column('connected_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('tenant_id', sa.Uuid(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint(
        'source_type', 'owner', 'repository', 'tenant_id',
        name='uq_sources_repo_tenant',
    ),
)
op.create_index('idx_sources_owner_repo',  'sources', ['owner', 'repository'])
op.create_index('idx_sources_source_type', 'sources', ['source_type'])
op.create_index('idx_sources_active',      'sources', ['active'])
op.create_index('idx_sources_tenant_id',   'sources', ['tenant_id'])
```

**Paso 4 — Agregar `tenant_id` a `evidence_records`**
```python
op.add_column('evidence_records',
    sa.Column('tenant_id', sa.Uuid(), nullable=True))
op.create_index('idx_evidence_tenant_id', 'evidence_records', ['tenant_id'])
```

**Paso 5 — Agregar `tenant_id` a `evaluation_records`**
```python
op.add_column('evaluation_records',
    sa.Column('tenant_id', sa.Uuid(), nullable=True))
op.create_index('idx_eval_tenant_id', 'evaluation_records', ['tenant_id'])
```

**Paso 6 — Índices faltantes en `evidence_records`**
```python
op.create_index(
    'uq_evidence_control_hash', 'evidence_records',
    ['control_id', 'evidence_hash', 'tenant_id'],
    unique=True,
)
op.create_index('idx_evidence_control_id',   'evidence_records', ['control_id'])
op.create_index('idx_evidence_collected_at', 'evidence_records', ['collected_at'])
```

**Paso 7 — Índices faltantes en `evaluation_records`**
```python
op.create_index('idx_eval_control_id',   'evaluation_records', ['control_id'])
op.create_index('idx_eval_status',       'evaluation_records', ['status'])
op.create_index('idx_eval_evaluated_at', 'evaluation_records', ['evaluated_at'])
op.create_index('idx_eval_source_repo',  'evaluation_records', ['source_repository'])
op.create_index('idx_eval_rule_id',      'evaluation_records', ['rule_id'])
```

---

### downgrade() — orden inverso estricto

```python
# 7 — Quitar índices de evaluation_records
op.drop_index('idx_eval_rule_id',       table_name='evaluation_records')
op.drop_index('idx_eval_source_repo',   table_name='evaluation_records')
op.drop_index('idx_eval_evaluated_at',  table_name='evaluation_records')
op.drop_index('idx_eval_status',        table_name='evaluation_records')
op.drop_index('idx_eval_control_id',    table_name='evaluation_records')
op.drop_index('idx_eval_tenant_id',     table_name='evaluation_records')
op.drop_column('evaluation_records', 'tenant_id')

# 6 — Quitar índices de evidence_records
op.drop_index('uq_evidence_control_hash', table_name='evidence_records')
op.drop_index('idx_evidence_collected_at', table_name='evidence_records')
op.drop_index('idx_evidence_control_id',   table_name='evidence_records')
op.drop_index('idx_evidence_tenant_id',    table_name='evidence_records')
op.drop_column('evidence_records', 'tenant_id')

# 5-4 — Eliminar tablas (rules antes que controls por FK)
op.drop_table('sources')
op.drop_table('rules')
op.drop_table('controls')
```

---

## TASK-02 — Actualizar ORM SQLAlchemy

**Archivo:** `src/securecode/adapters/postgres/models.py`

Agregar tres nuevas clases ORM y la columna `tenant_id` a las clases existentes.

### Clases nuevas a agregar

```python
from sqlalchemy.dialects.postgresql import JSONB

class Control(Base):
    __tablename__ = "controls"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    control_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="GitHub")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tenant_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

    rules: Mapped[list["Rule"]] = relationship(back_populates="control")


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    control_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("controls.control_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    allowlisted_fields: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tenant_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

    control: Mapped["Control"] = relationship(back_populates="rules")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="GitHub")
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repository: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tenant_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
```

### Columnas a agregar a clases existentes

En `EvidenceRecord`:
```python
tenant_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
```

En `EvaluationRecord`:
```python
tenant_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
```

---

## TASK-03 — Verificar schema parity

Después de aplicar la migración y actualizar el ORM, ejecutar:

```bash
cd C:\Users\achej\Documents\SecureCode
alembic check
```

`alembic check` compara `Base.metadata` (ORM) contra el estado real de la BD. Debe retornar sin diferencias. Si reporta columnas faltantes o extras, significa que el ORM y la migración están desincronizados.

**Criterio de aceptación:** salida limpia, sin líneas `"Detected added column"` ni `"Detected removed column"`.

---

## TASK-04 — Smoke test manual de la cadena completa

```bash
# BD limpia → head
alembic downgrade base
alembic upgrade head

# Verificar tablas existentes
psql $DATABASE_URL -c "\dt"
# Esperado: alembic_version, controls, evaluation_records, evidence_records, rules, sources, users

# Verificar columna tenant_id en tablas existentes
psql $DATABASE_URL -c "\d evidence_records"
psql $DATABASE_URL -c "\d evaluation_records"

# Verificar índices
psql $DATABASE_URL -c "\di" | grep -E "idx_|uq_"

# Downgrade completo
alembic downgrade base

# Upgrade again (idempotencia de la cadena)
alembic upgrade head
```

---

## TASK-05 — Tests de migración para el nuevo slice

**Archivo:** `tests/integration/test_migrations.py`  
**Acción:** Agregar los siguientes casos al archivo existente (no crear archivo nuevo).

### Test 1: Fresh install incluye tablas nuevas

```python
def test_fresh_install_includes_domain_schema(postgres_url, alembic_cfg):
    """Upgrade head desde BD vacía incluye controls, rules, sources."""
    engine = create_engine(postgres_url)
    _drop_all(engine)
    command.upgrade(alembic_cfg, "head")

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "controls" in tables
    assert "rules" in tables
    assert "sources" in tables

    # tenant_id en tablas existentes
    ev_cols = [c["name"] for c in inspector.get_columns("evidence_records")]
    eval_cols = [c["name"] for c in inspector.get_columns("evaluation_records")]
    assert "tenant_id" in ev_cols
    assert "tenant_id" in eval_cols
```

### Test 2: Datos legacy sobreviven la migración

```python
def test_legacy_data_survives_domain_schema(postgres_url, alembic_cfg):
    """Datos de GH-001/GH-002 insertados antes del domain_schema siguen accesibles."""
    engine = create_engine(postgres_url)
    _drop_all(engine)
    command.upgrade(alembic_cfg, "1bfdcaee6d14")  # hasta auth, sin domain_schema

    evidence_id = str(uuid4())
    eval_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO evidence_records (id, control_id, evidence_hash, raw_evidence, collected_at) "
            "VALUES (:id, :ctrl, :hash, :raw::jsonb, :ts)"
        ), {"id": evidence_id, "ctrl": "GH-001", "hash": "abc123",
            "raw": '{"required_review_approvals": 2}', "ts": now})

        conn.execute(text(
            "INSERT INTO evaluation_records "
            "(id, control_id, status, evaluated_at, evidence_id, source_type, source_repository, source_branch) "
            "VALUES (:id, :ctrl, :status, :ts, :eid, :stype, :repo, :branch)"
        ), {"id": eval_id, "ctrl": "GH-001", "status": "PASS", "ts": now,
            "eid": evidence_id, "stype": "GitHub", "repo": "org/repo", "branch": "main"})

    command.upgrade(alembic_cfg, "head")

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, tenant_id FROM evaluation_records WHERE id = :id"),
            {"id": eval_id}
        ).fetchone()
        assert row.status == "PASS"
        assert row.tenant_id is None   # legacy data: tenant_id NULL
```

### Test 3: UNIQUE constraint `(control_id, evidence_hash, tenant_id)` funciona

```python
def test_unique_evidence_hash_per_tenant(postgres_url, alembic_cfg):
    """Misma (control_id, hash) con tenant_id NULL solo puede insertarse una vez."""
    engine = create_engine(postgres_url)
    _drop_all(engine)
    command.upgrade(alembic_cfg, "head")
    now = datetime.now(timezone.utc).isoformat()

    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO evidence_records (id, control_id, evidence_hash, raw_evidence, collected_at) "
            "VALUES (:id, :ctrl, :hash, :raw::jsonb, :ts)"
        ), {"id": str(uuid4()), "ctrl": "GH-001", "hash": "dedup_hash",
            "raw": '{}', "ts": now})

        # Segunda inserción con mismo control_id + hash + tenant_id=NULL debe fallar
        from sqlalchemy.exc import IntegrityError
        import pytest
        with pytest.raises(IntegrityError):
            conn.execute(text(
                "INSERT INTO evidence_records (id, control_id, evidence_hash, raw_evidence, collected_at) "
                "VALUES (:id, :ctrl, :hash, :raw::jsonb, :ts)"
            ), {"id": str(uuid4()), "ctrl": "GH-001", "hash": "dedup_hash",
                "raw": '{}', "ts": now})
```

### Test 4: FK RESTRICT en `rules → controls`

```python
def test_fk_restrict_controls_rules(postgres_url, alembic_cfg):
    """DELETE en controls falla si existen rules referenciando ese control_id."""
    engine = create_engine(postgres_url)
    _drop_all(engine)
    command.upgrade(alembic_cfg, "head")
    now = datetime.now(timezone.utc).isoformat()

    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO controls (id, control_id, name, created_at, updated_at) "
            "VALUES (:id, :cid, :name, :ts, :ts)"
        ), {"id": str(uuid4()), "cid": "GH-TEST", "name": "Test Control", "ts": now})

        conn.execute(text(
            "INSERT INTO rules (id, rule_id, control_id, version, condition, allowlisted_fields, created_at) "
            "VALUES (:id, :rid, :cid, 1, :cond::jsonb, :af::jsonb, :ts)"
        ), {"id": str(uuid4()), "rid": "GH-TEST-RULE", "cid": "GH-TEST",
            "cond": '{"field":"x","operator":"EQ","value":true}',
            "af": '["x"]', "ts": now})

    from sqlalchemy.exc import IntegrityError
    import pytest
    with engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(text("DELETE FROM controls WHERE control_id = 'GH-TEST'"))
```

### Test 5: Downgrade completo restaura estado pre-domain_schema

```python
def test_downgrade_domain_schema(postgres_url, alembic_cfg):
    """Downgrade hasta 1bfdcaee6d14 elimina tablas nuevas y columnas tenant_id."""
    engine = create_engine(postgres_url)
    _drop_all(engine)
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "1bfdcaee6d14")

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "controls" not in tables
    assert "rules" not in tables
    assert "sources" not in tables

    ev_cols = [c["name"] for c in inspector.get_columns("evidence_records")]
    eval_cols = [c["name"] for c in inspector.get_columns("evaluation_records")]
    assert "tenant_id" not in ev_cols
    assert "tenant_id" not in eval_cols
```

---

## TASK-06 — Verificación final

Ejecutar el suite de integración completo (requiere PostgreSQL disponible):

```bash
cd C:\Users\achej\Documents\SecureCode
pytest tests/integration/test_migrations.py -v
```

**Criterio de aceptación:** todos los tests pasan, incluyendo los preexistentes y los 5 nuevos del TASK-05.

---

## Resumen de Archivos a Crear / Modificar

| Archivo | Acción | Task |
|---|---|---|
| `alembic/versions/<rev>_domain_schema.py` | CREAR | TASK-01 |
| `src/securecode/adapters/postgres/models.py` | MODIFICAR | TASK-02 |
| `tests/integration/test_migrations.py` | MODIFICAR (agregar tests) | TASK-05 |

---

## Orden de Ejecución

```
TASK-01 (migración)
    → TASK-02 (ORM)
        → TASK-03 (schema parity check)
            → TASK-04 (smoke test manual)
                → TASK-05 (tests de integración)
                    → TASK-06 (validación final)
                        → STOP
```

**STOP:** No implementar lógica de negocio sobre las nuevas tablas, no agregar endpoints, no modificar `evaluate_and_store_*.py`. Eso pertenece a specs posteriores.
