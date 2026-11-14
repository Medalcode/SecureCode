"""Transactional Enterprise Trial entitlement service.

This module contains no payment or revenue logic. It only enforces the
technical trial policy supplied by a caller and persists auditable state.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from securecode.adapters.postgres.models import (
    EnterpriseTrial,
    EnterpriseTrialRepository,
    EnterpriseTrialUsage,
    Organization,
    OrganizationMembership,
)


class TrialPolicyError(RuntimeError):
    """A deterministic entitlement, scope, or quota rejection."""


@dataclass(frozen=True)
class TrialPolicy:
    duration_days: int = 14
    repository_limit: int = 3
    evaluation_limit: int = 100

    def __post_init__(self) -> None:
        if not 1 <= self.duration_days <= 31:
            raise ValueError("Trial duration must be between 1 and 31 days.")
        if self.repository_limit < 1 or self.evaluation_limit < 1:
            raise ValueError("Trial quotas must be positive.")


DEFAULT_TRIAL_POLICY = TrialPolicy()


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def create_trial(
    session: Session,
    *,
    organization_name: str,
    owner_user_id: UUID,
    policy: TrialPolicy = DEFAULT_TRIAL_POLICY,
    now: datetime | None = None,
) -> EnterpriseTrial:
    """Create a tenant, initial owner membership, and inactive-after-expiry trial."""
    current = _utc(now or datetime.now(UTC))
    normalized_name = organization_name.strip()
    if not normalized_name:
        raise ValueError("Organization name is required.")
    organization = Organization(id=uuid4(), name=normalized_name, created_at=current)
    trial = EnterpriseTrial(
        id=uuid4(),
        organization_id=organization.id,
        starts_at=current,
        expires_at=current + timedelta(days=policy.duration_days),
        repository_limit=policy.repository_limit,
        evaluation_limit=policy.evaluation_limit,
        created_at=current,
    )
    membership = OrganizationMembership(
        id=uuid4(), organization_id=organization.id, user_id=owner_user_id, role="owner", created_at=current
    )
    session.add_all((organization, membership, trial))
    session.flush()
    return trial


def get_active_trial_for_user(session: Session, user_id: UUID, *, now: datetime | None = None) -> EnterpriseTrial | None:
    """Resolve one active trial through membership without cross-tenant lookup."""
    current = _utc(now or datetime.now(UTC))
    return (
        session.query(EnterpriseTrial)
        .join(OrganizationMembership, OrganizationMembership.organization_id == EnterpriseTrial.organization_id)
        .filter(OrganizationMembership.user_id == user_id, EnterpriseTrial.starts_at <= current, EnterpriseTrial.expires_at > current)
        .order_by(EnterpriseTrial.expires_at.asc())
        .first()
    )


def get_trial_for_user(session: Session, user_id: UUID) -> EnterpriseTrial | None:
    """Return the user's existing trial, including an expired one.

    A trial is intentionally a one-time entitlement.  Returning expired
    records lets an API reject a second activation instead of silently
    creating a new tenant and resetting a quota.
    """
    return (
        session.query(EnterpriseTrial)
        .join(OrganizationMembership, OrganizationMembership.organization_id == EnterpriseTrial.organization_id)
        .filter(OrganizationMembership.user_id == user_id)
        .order_by(EnterpriseTrial.created_at.asc())
        .first()
    )


def is_trial_owner(session: Session, *, trial_id: UUID, user_id: UUID) -> bool:
    """Only the tenant owner may expand the trial repository scope."""
    return (
        session.query(OrganizationMembership)
        .join(EnterpriseTrial, EnterpriseTrial.organization_id == OrganizationMembership.organization_id)
        .filter(
            EnterpriseTrial.id == trial_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.role == "owner",
        )
        .first()
        is not None
    )


def _locked_trial(session: Session, trial_id: UUID, now: datetime) -> EnterpriseTrial:
    trial = session.query(EnterpriseTrial).filter(EnterpriseTrial.id == trial_id).with_for_update().first()
    if trial is None:
        raise TrialPolicyError("Trial does not exist.")
    if not (_utc(trial.starts_at) <= now < _utc(trial.expires_at)):
        raise TrialPolicyError("Trial is expired or not active.")
    return trial


def authorize_repository(
    session: Session,
    *,
    trial_id: UUID,
    repository: str,
    now: datetime | None = None,
) -> EnterpriseTrialRepository:
    """Add one repository atomically; duplicate registration remains idempotent."""
    current = _utc(now or datetime.now(UTC))
    normalized_repository = repository.strip().lower()
    if not normalized_repository or "/" not in normalized_repository:
        raise ValueError("Repository must use owner/repo format.")
    trial = _locked_trial(session, trial_id, current)
    existing = (
        session.query(EnterpriseTrialRepository)
        .filter_by(trial_id=trial.id, repository=normalized_repository)
        .first()
    )
    if existing:
        return existing
    used = session.query(EnterpriseTrialRepository).filter_by(trial_id=trial.id).count()
    if used >= trial.repository_limit:
        raise TrialPolicyError("Trial repository quota reached.")
    registration = EnterpriseTrialRepository(
        id=uuid4(), trial_id=trial.id, repository=normalized_repository, created_at=current
    )
    session.add(registration)
    session.flush()
    return registration


def reserve_evaluation(
    session: Session,
    *,
    trial_id: UUID,
    repository: str,
    idempotency_key: str,
    now: datetime | None = None,
) -> EnterpriseTrialUsage:
    """Reserve one quota unit; retries with the same key reuse the reservation."""
    current = _utc(now or datetime.now(UTC))
    if not idempotency_key.strip() or len(idempotency_key) > 80:
        raise ValueError("Idempotency key must contain 1 to 80 characters.")
    normalized_repository = repository.strip().lower()
    trial = _locked_trial(session, trial_id, current)
    authorized = (
        session.query(EnterpriseTrialRepository)
        .filter_by(trial_id=trial.id, repository=normalized_repository)
        .first()
    )
    if authorized is None:
        raise TrialPolicyError("Repository is not authorized for this trial.")
    existing = (
        session.query(EnterpriseTrialUsage)
        .filter_by(trial_id=trial.id, idempotency_key=idempotency_key)
        .first()
    )
    if existing:
        return existing
    used = (
        session.query(EnterpriseTrialUsage)
        .filter(EnterpriseTrialUsage.trial_id == trial.id, EnterpriseTrialUsage.state.in_(("reserved", "completed")))
        .count()
    )
    if used >= trial.evaluation_limit:
        raise TrialPolicyError("Trial evaluation quota reached.")
    usage = EnterpriseTrialUsage(
        id=uuid4(), trial_id=trial.id, idempotency_key=idempotency_key, state="reserved", created_at=current
    )
    session.add(usage)
    session.flush()
    return usage


def complete_evaluation_reservation(
    session: Session,
    *,
    usage_id: UUID,
    evaluation_id: UUID,
    now: datetime | None = None,
) -> EnterpriseTrialUsage:
    """Mark a reservation complete only after persistence of an evaluation succeeds."""
    usage = session.query(EnterpriseTrialUsage).filter_by(id=usage_id).with_for_update().first()
    if usage is None:
        raise TrialPolicyError("Trial usage reservation does not exist.")
    if usage.state == "completed":
        if usage.evaluation_id != evaluation_id:
            raise TrialPolicyError("Idempotency key was already completed for another evaluation.")
        return usage
    if usage.state != "reserved":
        raise TrialPolicyError("Trial usage reservation is not active.")
    usage.state = "completed"
    usage.evaluation_id = evaluation_id
    usage.completed_at = _utc(now or datetime.now(UTC))
    session.flush()
    return usage


def release_evaluation_reservation(session: Session, *, usage_id: UUID) -> None:
    """Release a failed attempt so transient failures never consume a quota unit."""
    usage = session.query(EnterpriseTrialUsage).filter_by(id=usage_id).with_for_update().first()
    if usage is None:
        return
    if usage.state == "reserved":
        session.delete(usage)
        session.flush()
