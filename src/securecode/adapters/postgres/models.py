from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, DateTime, ForeignKey, JSON, Boolean, Integer, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_evidence: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Multi-tenancy prep: NULL = registro global / sin tenant activo.
    # UNIQUE incluye tenant_id: NULLs son distintos en B-tree → compatible con legacy.
    tenant_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

    __table_args__ = (
        # Declarado como Index(unique=True) para coincidir con op.create_index(..., unique=True)
        # en la migración ae4b780826f2. Un UniqueConstraint y un índice único son objetos
        # distintos para alembic check aunque garanticen la misma restricción.
        Index('uq_evidence_control_hash', 'control_id', 'evidence_hash', 'tenant_id', unique=True),
        Index('idx_evidence_control_id',   'control_id'),
        Index('idx_evidence_collected_at', 'collected_at'),
        Index('idx_evidence_tenant_id',    'tenant_id'),
    )

    # Relationship to evaluations
    evaluations: Mapped[list["EvaluationRecord"]] = relationship(back_populates="evidence")


class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Migration safety
    rule_version: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence_records.id"), nullable=False)
    requested_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_repository: Mapped[str] = mapped_column(String(255), nullable=False)
    source_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    # Multi-tenancy prep: NULL = registro global / sin tenant activo.
    tenant_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

    __table_args__ = (
        Index('idx_eval_control_id',   'control_id'),
        Index('idx_eval_status',       'status'),
        Index('idx_eval_evaluated_at', 'evaluated_at'),
        Index('idx_eval_source_repo',  'source_repository'),
        Index('idx_eval_rule_id',      'rule_id'),
        Index('idx_eval_tenant_id',    'tenant_id'),
    )

    # Relationship to evidence
    evidence: Mapped["EvidenceRecord"] = relationship(back_populates="evaluations")
    # Relationship to user
    requested_by: Mapped["User"] = relationship()


# ---------------------------------------------------------------------------
# Domain schema — migración ae4b780826f2_domain_schema
# ---------------------------------------------------------------------------

class Control(Base):
    """Catálogo maestro de controles GRC.

    Persiste lo que antes solo existía en ControlDefinition (Pydantic en memoria).
    control_id es el identificador de negocio (e.g. "GH-001"); UNIQUE global porque
    los IDs de control son referencias externas fijas del estándar GRC.
    active=False marca un control como retirado sin eliminar histórico.
    """
    __tablename__ = "controls"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    # uq_controls_control_id: el UniqueConstraint nombrado está en __table_args__
    # para que alembic check lo resuelva con el nombre exacto de la migración.
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="GitHub")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Multi-tenancy prep: NULL = control global (compartido por todos los tenants).
    tenant_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint('control_id', name='uq_controls_control_id'),
        Index('idx_controls_control_id',  'control_id'),
        Index('idx_controls_source_type', 'source_type'),
        Index('idx_controls_active',      'active'),
        Index('idx_controls_tenant_id',   'tenant_id'),
    )

    rules: Mapped[list["Rule"]] = relationship(back_populates="control")


class Rule(Base):
    """Historial versionado de RuleDefinition.

    Persiste lo que antes solo existía en rules/GH-001.json, rules/GH-002.json.
    (rule_id, version) UNIQUE: no pueden existir dos versiones iguales para la misma regla.
    FK → controls.control_id ON DELETE RESTRICT: el flujo correcto para retirar un control
    es active=False, nunca DELETE. RESTRICT es el seguro de red a nivel BD.
    """
    __tablename__ = "rules"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    control_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("controls.control_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # condition: JSON canónico de la condición (mismo formato que rules/GH-001.json)
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # allowlisted_fields: array JSON, e.g. ["required_review_approvals", "dismiss_stale_reviews"]
    allowlisted_fields: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Multi-tenancy prep: NULL = regla global.
    tenant_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint('rule_id', 'version', name='uq_rules_rule_version'),
        Index('idx_rules_control_id', 'control_id'),
        Index('idx_rules_rule_id',    'rule_id'),
        Index('idx_rules_active',     'active'),
        Index('idx_rules_tenant_id',  'tenant_id'),
    )

    control: Mapped["Control"] = relationship(back_populates="rules")


class Source(Base):
    """Conexiones reutilizables a fuentes de evidencia.

    Modela el paso 'conectar fuente (GitHub)' del flujo GRC.
    Antes source_type/repository/branch eran strings inline en cada evaluation_record.
    UNIQUE (source_type, owner, repository, tenant_id): tenant_id en el UNIQUE permite
    que dos organizaciones distintas conecten el mismo repositorio público.
    last_checked_at se actualiza en cada ejecución de evaluate_and_store_*.
    """
    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="GitHub")
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repository: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # NULL = fuente recién registrada, aún no evaluada.
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Multi-tenancy prep: incluido en UNIQUE para permitir múltiples orgs en el mismo repo.
    tenant_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint(
            'source_type', 'owner', 'repository', 'tenant_id',
            name='uq_sources_repo_tenant',
        ),
        Index('idx_sources_owner_repo',  'owner', 'repository'),
        Index('idx_sources_source_type', 'source_type'),
        Index('idx_sources_active',      'active'),
        Index('idx_sources_tenant_id',   'tenant_id'),
    )
