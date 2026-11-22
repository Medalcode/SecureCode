import os
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from securecode.adapters.postgres.models import Base

pytestmark = pytest.mark.postgres

EXPECTED_INDEXES = {
    ("enterprise_trial_usages", "ix_enterprise_trial_usages_trial_state", ("trial_id", "state")),
    ("organization_memberships", "ix_organization_memberships_user", ("user_id",)),
    ("subscription_events", "ix_subscription_events_user_occurred", ("user_id", "occurred_at")),
    ("user_audit_events", "ix_user_audit_events_target_created", ("target_user_id", "created_at")),
    ("user_sessions", "ix_user_sessions_user_active", ("user_id", "revoked_at")),
}


@pytest.fixture(scope="module")
def postgres_url():
    url = os.environ.get("DATABASE_URL")
    if not url or "sqlite" in url:
        if os.environ.get("REQUIRE_POSTGRES_TESTS") == "1":
            pytest.fail("DATABASE_URL must be provided for postgres tests in CI")
        pytest.skip("DATABASE_URL not configured for PostgreSQL")
    return url


def test_model_declares_migrated_indexes():
    declared = {
        (table.name, index.name, tuple(column.name for column in index.columns))
        for table in Base.metadata.tables.values()
        for index in table.indexes
    }
    for expected in EXPECTED_INDEXES:
        assert expected in declared


def test_migrated_indexes_exist_in_database(postgres_url):
    engine = create_engine(postgres_url)
    inspector = inspect(engine)
    actual = set()
    for table_name in {item[0] for item in EXPECTED_INDEXES}:
        for index in inspector.get_indexes(table_name):
            actual.add((table_name, index["name"], tuple(index["column_names"])))
    engine.dispose()
    assert EXPECTED_INDEXES <= actual


def test_audit_details_is_jsonb_in_database(postgres_url):
    engine = create_engine(postgres_url)
    inspector = inspect(engine)
    column = next(item for item in inspector.get_columns("user_audit_events") if item["name"] == "details")
    engine.dispose()
    assert "JSONB" in str(column["type"]).upper()


def test_alembic_check_has_no_schema_drift(postgres_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", postgres_url.replace("%", "%%"))
    command.check(config)
