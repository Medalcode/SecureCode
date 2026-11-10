from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import String, DateTime, ForeignKey, JSON, Boolean
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
    # Roles are deliberately small and explicit. Authorization decisions never
    # depend on client-supplied labels.
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="auditor", server_default="auditor")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserAuditEvent(Base):
    """Immutable security-relevant lifecycle event for an account."""

    __tablename__ = "user_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    target_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class UserSettings(Base):
    """Safe, user-owned presentation and evaluation defaults.

    This model deliberately excludes integration credentials and canonical rules.
    """

    __tablename__ = "user_settings"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    default_repository: Mapped[str | None] = mapped_column(String(200), nullable=True)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main", server_default="main")
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="es-CL", server_default="es-CL")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Santiago", server_default="America/Santiago")
    theme: Mapped[str] = mapped_column(String(16), nullable=False, default="system", server_default="system")
    notify_evaluation_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    notify_evaluation_failure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    notify_weekly_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class UserSubscription(Base):
    """Current non-billable subscription state for one SecureCode account."""

    __tablename__ = "user_subscriptions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(32), nullable=False, default="pro", server_default="pro")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SubscriptionEvent(Base):
    """Append-only history of confirmed subscription changes."""

    __tablename__ = "subscription_events"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    previous_plan_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_plan_id: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)


class UserFinOpsSettings(Base):
    """Per-account FinOps alert preferences; not a Cloud Billing source."""

    __tablename__ = "user_finops_settings"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    budget_clp: Mapped[int] = mapped_column(nullable=False, default=1000, server_default="1000")
    alert_threshold_pct: Mapped[int] = mapped_column(nullable=False, default=80, server_default="80")
    alert_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    
    id: Mapped[UUID] = mapped_column(primary_key=True)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_evidence: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Relationship to evaluations
    evaluations: Mapped[list["EvaluationRecord"]] = relationship(back_populates="evidence")

class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"
    
    id: Mapped[UUID] = mapped_column(primary_key=True)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=True) # Migration safety
    rule_version: Mapped[int] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_id: Mapped[UUID] = mapped_column(ForeignKey("evidence_records.id"), nullable=False)
    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_repository: Mapped[str] = mapped_column(String(255), nullable=False)
    source_branch: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationship to evidence
    evidence: Mapped["EvidenceRecord"] = relationship(back_populates="evaluations")
    
    # Relationship to user
    requested_by: Mapped["User"] = relationship()
