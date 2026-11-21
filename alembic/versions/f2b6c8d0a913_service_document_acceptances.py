"""add append-only service document acceptances

Revision ID: f2b6c8d0a913
Revises: c1a4d9e7f205
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2b6c8d0a913"
down_revision: str | Sequence[str] | None = "c1a4d9e7f205"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_document_acceptances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.String(length=64), nullable=False),
        sa.Column("package_version", sa.String(length=32), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("document_version", sa.String(length=32), nullable=False),
        sa.Column("document_sha256", sa.String(length=64), nullable=False),
        sa.Column("package_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_path", sa.String(length=255), nullable=False),
        sa.Column("acceptance_type", sa.String(length=64), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_document_acceptances_org_accepted_at", "service_document_acceptances", ["organization_id", "accepted_at"])
    op.create_index("ix_service_document_acceptances_user_accepted_at", "service_document_acceptances", ["user_id", "accepted_at"])


def downgrade() -> None:
    op.drop_index("ix_service_document_acceptances_user_accepted_at", table_name="service_document_acceptances")
    op.drop_index("ix_service_document_acceptances_org_accepted_at", table_name="service_document_acceptances")
    op.drop_table("service_document_acceptances")
