from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from securecode.domain.roles import ANALYST


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
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=ANALYST, server_default=ANALYST)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_active", "user_id", "revoked_at"),
        UniqueConstraint("jti", name="uq_user_sessions_jti"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    jti: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    csrf_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Organization(Base):
    """A tenant that owns Enterprise Trial quotas and memberships."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class OrganizationMembership(Base):
    """Explicit user-to-tenant relation; this MVP allows one tenant per user."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_membership"),
        UniqueConstraint("user_id", name="uq_organization_memberships_user"),
        Index("ix_organization_memberships_user", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=ANALYST, server_default=ANALYST)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class EnterpriseTrial(Base):
    """Time-limited tenant entitlement; it is not a billing record."""

    __tablename__ = "enterprise_trials"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), unique=True, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    repository_limit: Mapped[int] = mapped_column(nullable=False, default=3, server_default="3")
    evaluation_limit: Mapped[int] = mapped_column(nullable=False, default=100, server_default="100")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class EnterpriseTrialRepository(Base):
    """Repository scope explicitly authorized for a tenant trial."""

    __tablename__ = "enterprise_trial_repositories"
    __table_args__ = (UniqueConstraint("trial_id", "repository", name="uq_enterprise_trial_repository"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trial_id: Mapped[UUID] = mapped_column(ForeignKey("enterprise_trials.id"), nullable=False)
    repository: Mapped[str] = mapped_column(String(201), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class EnterpriseTrialUsage(Base):
    """Transactional reservation so concurrent requests cannot overrun a trial quota."""

    __tablename__ = "enterprise_trial_usages"
    __table_args__ = (
        UniqueConstraint("trial_id", "idempotency_key", name="uq_enterprise_trial_usage_key"),
        Index("ix_enterprise_trial_usages_trial_state", "trial_id", "state"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trial_id: Mapped[UUID] = mapped_column(ForeignKey("enterprise_trials.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="reserved", server_default="reserved")
    evaluation_id: Mapped[UUID | None] = mapped_column(ForeignKey("evaluation_records.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserAuditEvent(Base):
    """Immutable security-relevant lifecycle event for an account."""

    __tablename__ = "user_audit_events"
    __table_args__ = (Index("ix_user_audit_events_target_created", "target_user_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    target_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


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
    __table_args__ = (Index("ix_subscription_events_user_occurred", "user_id", "occurred_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    previous_plan_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_plan_id: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)


class ServiceDocumentAcceptance(Base):
    """Append-only proof that an owner accepted a published document bundle."""

    __tablename__ = "service_document_acceptances"
    __table_args__ = (
        Index("ix_service_document_acceptances_org_accepted_at", "organization_id", "accepted_at"),
        Index("ix_service_document_acceptances_user_accepted_at", "user_id", "accepted_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    package_id: Mapped[str] = mapped_column(String(64), nullable=False)
    package_version: Mapped[str] = mapped_column(String(32), nullable=False)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_version: Mapped[str] = mapped_column(String(32), nullable=False)
    document_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    package_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_path: Mapped[str] = mapped_column(String(255), nullable=False)
    acceptance_type: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    organization: Mapped["Organization"] = relationship()
    user: Mapped["User"] = relationship()


class UserFinOpsSettings(Base):
    """Per-account FinOps alert preferences; not a Cloud Billing source."""

    __tablename__ = "user_finops_settings"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    budget_clp: Mapped[int] = mapped_column(nullable=False, default=1000, server_default="1000")
    alert_threshold_pct: Mapped[int] = mapped_column(nullable=False, default=80, server_default="80")
    alert_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class RepositoryAuthorization(Base):
    """Explicit repository scope assigned to an analyst by an organization owner."""

    __tablename__ = "repository_authorizations"
    __table_args__ = (
        UniqueConstraint("user_id", "repository", name="uq_repository_authorization_user_repository"),
        Index("ix_repository_authorizations_user_active", "user_id", "active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    repository: Mapped[str] = mapped_column(String(201), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class LoginAttempt(Base):
    """Privacy-preserving, database-backed login throttle state."""

    __tablename__ = "login_attempts"

    scope_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    failure_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
