import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from alembic import command
from securecode.adapters.postgres.models import (
    EnterpriseTrial,
    EnterpriseTrialUsage,
    EvaluationRecord,
    EvidenceRecord,
    Organization,
    OrganizationMembership,
    ServiceDocumentAcceptance,
    User,
)

EXPECTED_TABLES = {
    "alembic_version",
    "enterprise_trial_repositories",
    "enterprise_trial_usages",
    "enterprise_trials",
    "evaluation_records",
    "evidence_records",
    "login_attempts",
    "organization_memberships",
    "organizations",
    "repository_authorizations",
    "service_document_acceptances",
    "subscription_events",
    "user_audit_events",
    "user_finops_settings",
    "user_settings",
    "user_sessions",
    "user_subscriptions",
    "users",
}

EXPECTED_INDEXES = {
    ("enterprise_trial_usages", "ix_enterprise_trial_usages_trial_state"),
    ("organization_memberships", "ix_organization_memberships_user"),
    ("repository_authorizations", "ix_repository_authorizations_user_active"),
    ("service_document_acceptances", "ix_service_document_acceptances_org_accepted_at"),
    ("service_document_acceptances", "ix_service_document_acceptances_user_accepted_at"),
    ("subscription_events", "ix_subscription_events_user_occurred"),
    ("user_audit_events", "ix_user_audit_events_target_created"),
    ("user_sessions", "ix_user_sessions_user_active"),
}

EXPECTED_CONSTRAINTS = {
    ("enterprise_trial_usages", "uq_enterprise_trial_usage_key"),
    ("organization_memberships", "uq_organization_membership"),
    ("organization_memberships", "uq_organization_memberships_user"),
    ("repository_authorizations", "uq_repository_authorization_user_repository"),
    ("user_sessions", "uq_user_sessions_jti"),
}

ACCEPTANCE_COLUMNS = {
    "package_id",
    "package_version",
    "document_id",
    "document_version",
    "document_sha256",
    "package_sha256",
    "source_path",
    "acceptance_type",
    "accepted_at",
}


def _alembic_config(database_url: str) -> Config:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def _inspect_schema(engine) -> dict:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    indexes = {
        (table, index["name"])
        for table in tables
        for index in inspector.get_indexes(table)
    }
    constraints = {
        (table, constraint["name"])
        for table in tables
        for constraint in inspector.get_unique_constraints(table)
    }
    details = next(item for item in inspector.get_columns("user_audit_events") if item["name"] == "details")
    acceptance = {item["name"] for item in inspector.get_columns("service_document_acceptances")}

    assert EXPECTED_TABLES <= tables
    assert EXPECTED_INDEXES <= indexes
    assert EXPECTED_CONSTRAINTS <= constraints
    assert "JSONB" in str(details["type"]).upper()
    assert ACCEPTANCE_COLUMNS <= acceptance

    return {
        "tables": len(tables),
        "indexes": len(indexes),
        "unique_constraints": len(constraints),
        "audit_details_type": str(details["type"]),
        "acceptance_columns": sorted(ACCEPTANCE_COLUMNS),
    }


def _insert_sample(session) -> dict:
    now = datetime.now(UTC)
    user_id = uuid4()
    organization_id = uuid4()
    membership_id = uuid4()
    trial_id = uuid4()
    usage_id = uuid4()
    evidence_id = uuid4()
    evaluation_id = uuid4()
    acceptance_id = uuid4()

    user = User(
        id=user_id,
        username=f"fresh-install-{uuid4().hex[:12]}@test.invalid",
        password_hash="not-a-real-password-hash",
        active=True,
        role="analyst",
        created_at=now,
        updated_at=now,
    )
    organization = Organization(
        id=organization_id,
        name=f"Fresh Install {uuid4().hex[:12]}",
        created_at=now,
    )
    membership = OrganizationMembership(
        id=membership_id,
        organization_id=organization_id,
        user_id=user_id,
        role="analyst",
        created_at=now,
    )
    evidence = EvidenceRecord(
        id=evidence_id,
        control_id="GH-001",
        evidence_hash="0" * 64,
        raw_evidence={"required_review_approvals": 2, "dismiss_stale_reviews": True},
        collected_at=now,
    )
    evaluation = EvaluationRecord(
        id=evaluation_id,
        control_id="GH-001",
        rule_id="GH-001-RULE",
        rule_version=1,
        status="PASS",
        evaluated_at=now,
        evidence_id=evidence_id,
        requested_by_user_id=user_id,
        source_type="github",
        source_repository="test/test",
        source_branch="main",
    )
    trial = EnterpriseTrial(
        id=trial_id,
        organization_id=organization_id,
        starts_at=now,
        expires_at=now,
        repository_limit=3,
        evaluation_limit=100,
        created_at=now,
    )
    usage = EnterpriseTrialUsage(
        id=usage_id,
        trial_id=trial_id,
        idempotency_key="fresh-install",
        state="reserved",
        evaluation_id=evaluation_id,
        created_at=now,
    )
    acceptance = ServiceDocumentAcceptance(
        id=acceptance_id,
        organization_id=organization_id,
        user_id=user_id,
        package_id="SECURECODE-ONBOARDING",
        package_version="2026-11-20.1",
        document_id="SERVICE_TERMS",
        document_version="2026-11-20.1",
        document_sha256="0" * 64,
        package_sha256="0" * 64,
        source_path="/legal/terminos",
        acceptance_type="organization_registration",
        accepted_at=now,
    )
    session.add_all((user, organization, evidence))
    session.flush()
    session.add_all((membership, evaluation, trial))
    session.flush()
    session.add_all((usage, acceptance))
    session.commit()
    return {
        "user_id": str(user_id),
        "organization_id": str(organization_id),
        "evaluation_id": str(evaluation_id),
        "acceptance_id": str(acceptance_id),
    }


def _assert_integrity(session, user_id: UUID) -> None:
    duplicate_org_id = uuid4()
    session.add(
        Organization(
            id=duplicate_org_id,
            name=f"Duplicate Target {uuid4().hex[:12]}",
            created_at=datetime.now(UTC),
        )
    )
    session.flush()
    session.add(
        OrganizationMembership(
            id=uuid4(),
            organization_id=duplicate_org_id,
            user_id=user_id,
            role="analyst",
            created_at=datetime.now(UTC),
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    else:
        raise AssertionError("duplicate cross-tenant membership was not rejected")

    session.add(
        OrganizationMembership(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=user_id,
            role="analyst",
            created_at=datetime.now(UTC),
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    else:
        raise AssertionError("membership with missing organization was not rejected")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a clean PostgreSQL installation from Alembic migrations")
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    database_url = args.database_url.strip()
    if "postgres" not in database_url:
        raise SystemExit("A PostgreSQL DATABASE_URL is required")
    os.environ["DATABASE_URL"] = database_url

    config = _alembic_config(database_url)
    command.upgrade(config, "head")
    command.check(config)

    engine = create_engine(database_url)
    schema = _inspect_schema(engine)
    session = sessionmaker(bind=engine)()
    sample = _insert_sample(session)
    _assert_integrity(session, UUID(sample["user_id"]))
    session.close()
    engine.dispose()

    print(
        json.dumps(
            {
                "database": "isolated-empty-postgresql",
                "alembic_head": ScriptDirectory.from_config(config).get_current_head(),
                "schema": schema,
                "sample": sample,
                "alembic_check": "clean",
                "referential_integrity": "enforced",
                "tenant_uniqueness": "enforced",
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
