from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from postgres_backup_lib import (
    alembic_head,
    assert_database_allowed,
    assert_loopback_host,
    assert_test_environment,
    connection_secrets,
    parse_database_url,
    sqlalchemy_url,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from securecode.adapters.postgres.models import (
    EnterpriseTrial,
    EnterpriseTrialRepository,
    EnterpriseTrialUsage,
    EvaluationRecord,
    EvidenceRecord,
    LoginAttempt,
    Organization,
    OrganizationMembership,
    RepositoryAuthorization,
    ServiceDocumentAcceptance,
    SubscriptionEvent,
    User,
    UserAuditEvent,
    UserFinOpsSettings,
    UserSession,
    UserSettings,
    UserSubscription,
)
from securecode.api.security import hash_password
from securecode.api.service_documents import current_onboarding_package

EXPECTED_HEAD = "d4e9f1a2b3c4"
FIXTURE_NAMES = ("SecureCode Backup Fixture Org A", "SecureCode Backup Fixture Org B")


def _evidence_hash(control_id: str, repository: str, raw: dict) -> str:
    payload = {"control_id": control_id, "repository": repository, "raw_evidence": raw}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def seed_synthetic_dataset(
    database_url: str,
    allowed_database: str,
    environment: str = "test",
) -> dict:
    started = datetime.now(UTC)
    parsed = parse_database_url(database_url)
    secrets_to_hide = connection_secrets(parsed)
    assert_test_environment(environment)
    assert_loopback_host(parsed.host)
    assert_database_allowed(parsed.database, [allowed_database])
    if alembic_head(parsed) != EXPECTED_HEAD:
        raise RuntimeError("Synthetic fixture requires the expected Alembic head")

    engine = create_engine(sqlalchemy_url(parsed))
    session = sessionmaker(bind=engine)()
    try:
        existing = session.query(Organization).filter(Organization.name.in_(FIXTURE_NAMES)).count()
        if existing:
            raise RuntimeError("Synthetic fixture organizations already exist; no changes were made")

        package = current_onboarding_package()
        generated_password = secrets.token_urlsafe(24)
        password_hash = hash_password(generated_password)
        del generated_password

        owners: list[User] = []
        analysts: list[User] = []
        organizations: list[Organization] = []
        for suffix in ("a", "b"):
            owners.append(
                User(
                    id=uuid4(),
                    username=f"backup-owner-{suffix}@example.test",
                    password_hash=password_hash,
                    active=True,
                    role="owner",
                    created_at=started,
                    updated_at=started,
                )
            )
            analysts.append(
                User(
                    id=uuid4(),
                    username=f"backup-analyst-{suffix}@example.test",
                    password_hash=password_hash,
                    active=True,
                    role="analyst",
                    created_at=started,
                    updated_at=started,
                )
            )
            organizations.append(
                Organization(
                    id=uuid4(),
                    name=f"SecureCode Backup Fixture Org {suffix.upper()}",
                    created_at=started,
                )
            )

        all_users = owners + analysts
        session.add_all(all_users)
        session.add_all(organizations)
        session.flush()

        trials: list[EnterpriseTrial] = []
        for organization in organizations:
            trials.append(
                EnterpriseTrial(
                    id=uuid4(),
                    organization_id=organization.id,
                    starts_at=started - timedelta(days=1),
                    expires_at=started + timedelta(days=30),
                    repository_limit=3,
                    evaluation_limit=100,
                    created_at=started,
                )
            )
        session.add_all(trials)
        session.flush()

        memberships = []
        authorizations = []
        settings = []
        finops = []
        subscriptions = []
        subscription_events = []
        for owner, analyst, organization, trial in zip(owners, analysts, organizations, trials):
            memberships.extend(
                (
                    OrganizationMembership(
                        id=uuid4(),
                        organization_id=organization.id,
                        user_id=owner.id,
                        role="owner",
                        created_at=started,
                    ),
                    OrganizationMembership(
                        id=uuid4(),
                        organization_id=organization.id,
                        user_id=analyst.id,
                        role="analyst",
                        created_at=started,
                    ),
                )
            )
            authorizations.append(
                RepositoryAuthorization(
                    id=uuid4(),
                    user_id=analyst.id,
                    repository=f"fixture/{organization.name.rsplit(' ', 1)[-1].lower()}",
                    active=True,
                    created_at=started,
                    updated_at=started,
                )
            )
            session.add(
                EnterpriseTrialRepository(
                    id=uuid4(),
                    trial_id=trial.id,
                    repository=f"fixture/{organization.name.rsplit(' ', 1)[-1].lower()}",
                    created_at=started,
                )
            )
            settings.extend(
                (
                    UserSettings(user_id=owner.id, default_repository="fixture/shared", updated_at=started),
                    UserSettings(user_id=analyst.id, default_repository="fixture/shared", updated_at=started),
                )
            )
            finops.extend(
                (
                    UserFinOpsSettings(user_id=owner.id, budget_clp=50000, updated_at=started),
                    UserFinOpsSettings(user_id=analyst.id, budget_clp=25000, updated_at=started),
                )
            )
            for user in (owner, analyst):
                subscriptions.append(
                    UserSubscription(
                        user_id=user.id,
                        plan_id="enterprise_trial",
                        started_at=started - timedelta(days=1),
                        expires_at=started + timedelta(days=30),
                        last_changed_at=started - timedelta(days=1),
                    )
                )
                subscription_events.append(
                    SubscriptionEvent(
                        id=uuid4(),
                        user_id=user.id,
                        previous_plan_id=None,
                        new_plan_id="enterprise_trial",
                        occurred_at=started - timedelta(days=1),
                        effective_from=started - timedelta(days=1),
                        effective_until=started + timedelta(days=30),
                        event_type="fixture_seed",
                    )
                )
        session.add_all(memberships)
        session.add_all(authorizations)
        session.add_all(settings)
        session.add_all(finops)
        session.add_all(subscriptions)
        session.add_all(subscription_events)
        session.flush()

        control_matrix = {
            "GH-001": {"required_review_approvals": 2, "dismiss_stale_reviews": True},
            "GH-002": {"branch_protection_required": True, "allow_force_pushes": False},
            "GH-003": {"secret_scanning_enabled": True, "push_protection_enabled": True},
        }
        statuses = {"GH-001": "PASS", "GH-002": "FAIL", "GH-003": "PASS"}
        evidences = []
        evaluations = []
        for analyst, organization in zip(analysts, organizations):
            repository = f"fixture/{organization.name.rsplit(' ', 1)[-1].lower()}"
            for control_id, raw_evidence in control_matrix.items():
                evidence = EvidenceRecord(
                    id=uuid4(),
                    control_id=control_id,
                    evidence_hash=_evidence_hash(control_id, repository, raw_evidence),
                    raw_evidence=raw_evidence,
                    collected_at=started,
                )
                evidences.append(evidence)
                evaluations.append(
                    EvaluationRecord(
                        id=uuid4(),
                        control_id=control_id,
                        rule_id=f"{control_id}-RULE",
                        rule_version=1,
                        status=statuses[control_id],
                        evaluated_at=started,
                        evidence_id=evidence.id,
                        requested_by_user_id=analyst.id,
                        source_type="github",
                        source_repository=repository,
                        source_branch="main",
                    )
                )
        session.add_all(evidences)
        session.flush()
        session.add_all(evaluations)
        session.flush()

        usages = []
        for trial, evaluation in zip(trials, evaluations[: len(trials)]):
            usages.append(
                EnterpriseTrialUsage(
                    id=uuid4(),
                    trial_id=trial.id,
                    idempotency_key=f"backup-fixture-{evaluation.id}",
                    state="completed",
                    evaluation_id=evaluation.id,
                    created_at=started,
                    completed_at=started,
                )
            )
        session.add_all(usages)

        acceptances = []
        for owner, organization in zip(owners, organizations):
            for document in package.documents:
                acceptances.append(
                    ServiceDocumentAcceptance(
                        id=uuid4(),
                        organization_id=organization.id,
                        user_id=owner.id,
                        package_id=package.package_id,
                        package_version=package.version,
                        document_id=document.document_id,
                        document_version=document.version,
                        document_sha256=document.sha256,
                        package_sha256=package.sha256,
                        source_path=document.path,
                        acceptance_type="organization_registration",
                        accepted_at=started,
                    )
                )
        session.add_all(acceptances)

        audit_events = []
        sessions = []
        for owner, analyst, organization in zip(owners, analysts, organizations):
            audit_events.append(
                UserAuditEvent(
                    id=uuid4(),
                    actor_user_id=owner.id,
                    target_user_id=analyst.id,
                    action="backup_fixture_membership_created",
                    details={"organization": organization.name, "role": "analyst"},
                    created_at=started,
                )
            )
            sessions.append(
                UserSession(
                    id=uuid4(),
                    user_id=analyst.id,
                    jti=secrets.token_hex(32),
                    created_at=started,
                    expires_at=started + timedelta(hours=1),
                    last_seen_at=started,
                    csrf_token_hash=secrets.token_hex(32),
                )
            )
        session.add_all(audit_events)
        session.add_all(sessions)
        session.add(
            LoginAttempt(
                scope_hash=secrets.token_hex(32),
                failure_count=2,
                window_started_at=started,
                locked_until=None,
                updated_at=started,
            )
        )
        session.commit()
        summary = {
            "status": "ok",
            "database": parsed.database,
            "organizations": [str(item.id) for item in organizations],
            "users": [str(item.id) for item in all_users],
            "trials": [str(item.id) for item in trials],
            "evaluations": len(evaluations),
            "evidences": len(evidences),
            "acceptances": len(acceptances),
            "sessions": len(sessions),
            "audit_events": len(audit_events),
        }
    except Exception as error:
        session.rollback()
        message = str(error)
        for secret in secrets_to_hide:
            message = message.replace(secret, "***")
        raise RuntimeError(message) from error
    finally:
        session.close()
        engine.dispose()

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic two-tenant data for backup verification")
    parser.add_argument("--environment", default="test")
    parser.add_argument("--allowed-database", required=True)
    args = parser.parse_args()
    source_url = os.environ.get("BACKUP_SOURCE_DATABASE_URL", "")
    if not source_url:
        raise SystemExit("BACKUP_SOURCE_DATABASE_URL is required")
    result = seed_synthetic_dataset(source_url, args.allowed_database, args.environment)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
