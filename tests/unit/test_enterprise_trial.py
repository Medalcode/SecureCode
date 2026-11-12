"""Enterprise Trial policy tests using an isolated in-memory database."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from securecode.adapters.postgres.models import Base, OrganizationMembership, User
from securecode.api.security import hash_password
from securecode.application.enterprise_trial import (
    TrialPolicyError,
    authorize_repository,
    create_trial,
    get_active_trial_for_user,
    release_evaluation_reservation,
    reserve_evaluation,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session
    engine.dispose()


def _user(session: Session, username: str) -> User:
    user = User(id=uuid4(), username=username, password_hash=hash_password("Password!123"), active=True)
    session.add(user)
    session.flush()
    return user


def _trial(session: Session, *, now: datetime | None = None):
    owner = _user(session, "owner@example.com")
    trial = create_trial(session, organization_name="Example Ltd", owner_user_id=owner.id, now=now)
    return owner, trial


def test_trial_allows_three_repositories_and_rejects_a_fourth(session):
    _, trial = _trial(session)
    for repository in ("Acme/One", "Acme/Two", "Acme/Three"):
        authorize_repository(session, trial_id=trial.id, repository=repository)

    with pytest.raises(TrialPolicyError, match="repository quota"):
        authorize_repository(session, trial_id=trial.id, repository="Acme/Four")


def test_trial_allows_one_hundred_evaluations_and_blocks_one_hundred_one(session):
    _, trial = _trial(session)
    authorize_repository(session, trial_id=trial.id, repository="Acme/One")
    for sequence in range(100):
        reserve_evaluation(
            session,
            trial_id=trial.id,
            repository="acme/one",
            idempotency_key=f"evaluation-{sequence}",
        )

    with pytest.raises(TrialPolicyError, match="evaluation quota"):
        reserve_evaluation(
            session, trial_id=trial.id, repository="acme/one", idempotency_key="evaluation-101"
        )


def test_idempotency_and_failed_reservation_do_not_double_consume_quota(session):
    _, trial = _trial(session)
    authorize_repository(session, trial_id=trial.id, repository="Acme/One")
    first = reserve_evaluation(
        session, trial_id=trial.id, repository="acme/one", idempotency_key="same-request"
    )
    retry = reserve_evaluation(
        session, trial_id=trial.id, repository="acme/one", idempotency_key="same-request"
    )
    assert retry.id == first.id

    release_evaluation_reservation(session, usage_id=first.id)
    replacement = reserve_evaluation(
        session, trial_id=trial.id, repository="acme/one", idempotency_key="replacement"
    )
    assert replacement.id != first.id


def test_expired_trial_and_cross_tenant_user_cannot_use_trial_scope(session):
    start = datetime(2026, 11, 1, tzinfo=UTC)
    owner, trial = _trial(session, now=start)
    authorize_repository(session, trial_id=trial.id, repository="Acme/One", now=start)
    outsider = _user(session, "outsider@example.com")
    assert get_active_trial_for_user(session, outsider.id, now=start + timedelta(days=1)) is None
    assert get_active_trial_for_user(session, owner.id, now=start + timedelta(days=1)).id == trial.id

    with pytest.raises(TrialPolicyError, match="expired"):
        reserve_evaluation(
            session,
            trial_id=trial.id,
            repository="acme/one",
            idempotency_key="after-expiry",
            now=start + timedelta(days=14),
        )


def test_member_resolves_only_its_own_organization_trial(session):
    owner_one, trial_one = _trial(session)
    owner_two = _user(session, "other-owner@example.com")
    trial_two = create_trial(session, organization_name="Other Ltd", owner_user_id=owner_two.id)
    member = _user(session, "member@example.com")
    session.add(
        OrganizationMembership(
            id=uuid4(), organization_id=trial_two.organization_id, user_id=member.id, role="member"
        )
    )
    session.flush()

    assert get_active_trial_for_user(session, member.id).id == trial_two.id
    assert get_active_trial_for_user(session, owner_one.id).id == trial_one.id
