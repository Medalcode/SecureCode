"""add enterprise trial tenant quotas

Revision ID: aa7c1e9d4f30
Revises: f9b2e4a7c308
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "aa7c1e9d4f30"
down_revision: str | Sequence[str] | None = "f9b2e4a7c308"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_membership"),
    )
    op.create_table(
        "enterprise_trials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("repository_limit", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("evaluation_limit", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id"),
    )
    op.create_table(
        "enterprise_trial_repositories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trial_id", sa.Uuid(), nullable=False),
        sa.Column("repository", sa.String(length=201), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trial_id"], ["enterprise_trials.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trial_id", "repository", name="uq_enterprise_trial_repository"),
    )
    op.create_table(
        "enterprise_trial_usages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trial_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="reserved"),
        sa.Column("evaluation_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluation_records.id"]),
        sa.ForeignKeyConstraint(["trial_id"], ["enterprise_trials.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trial_id", "idempotency_key", name="uq_enterprise_trial_usage_key"),
    )
    op.create_index("ix_organization_memberships_user", "organization_memberships", ["user_id"])
    op.create_index("ix_enterprise_trial_usages_trial_state", "enterprise_trial_usages", ["trial_id", "state"])


def downgrade() -> None:
    op.drop_index("ix_enterprise_trial_usages_trial_state", table_name="enterprise_trial_usages")
    op.drop_index("ix_organization_memberships_user", table_name="organization_memberships")
    op.drop_table("enterprise_trial_usages")
    op.drop_table("enterprise_trial_repositories")
    op.drop_table("enterprise_trials")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
