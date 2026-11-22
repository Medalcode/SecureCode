import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from securecode.adapters.postgres.models import (
    Base,
    Organization,
    OrganizationMembership,
    User,
)

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not DATABASE_URL or "postgresql" not in DATABASE_URL,
        reason="Requires PostgreSQL DATABASE_URL",
    ),
]


@pytest.fixture
def engine():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def _seed_account(engine):
    now = datetime.now(UTC)
    user_id = uuid4()
    organization_ids = (uuid4(), uuid4())
    with sessionmaker(bind=engine)() as session:
        session.add(User(
            id=user_id,
            username=f"member-{uuid4().hex}@test.invalid",
            password_hash="synthetic-hash",
            active=True,
            role="analyst",
            created_at=now,
        ))
        for index, organization_id in enumerate(organization_ids):
            session.add(Organization(
                id=organization_id,
                name=f"Membership Test {uuid4().hex[:12]} {index}",
                created_at=now,
            ))
        session.commit()
    return user_id, organization_ids


def test_duplicate_membership_is_rejected(engine):
    user_id, organization_ids = _seed_account(engine)
    now = datetime.now(UTC)
    with sessionmaker(bind=engine)() as session:
        session.add(OrganizationMembership(
            id=uuid4(),
            organization_id=organization_ids[0],
            user_id=user_id,
            role="analyst",
            created_at=now,
        ))
        session.commit()
        session.add(OrganizationMembership(
            id=uuid4(),
            organization_id=organization_ids[1],
            user_id=user_id,
            role="analyst",
            created_at=now,
        ))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_concurrent_duplicate_membership_is_rejected(engine):
    user_id, organization_ids = _seed_account(engine)
    now = datetime.now(UTC)
    barrier = threading.Barrier(2)

    def insert(organization_id):
        local_engine = create_engine(DATABASE_URL)
        with sessionmaker(bind=local_engine)() as session:
            try:
                barrier.wait(timeout=20)
                session.add(OrganizationMembership(
                    id=uuid4(),
                    organization_id=organization_id,
                    user_id=user_id,
                    role="analyst",
                    created_at=now,
                ))
                session.commit()
                return "ok"
            except IntegrityError:
                session.rollback()
                return "conflict"
            finally:
                local_engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(insert, organization_ids))

    assert sorted(results) == ["conflict", "ok"]
