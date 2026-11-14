"""introduce explicit SecureCode platform and organization roles

Revision ID: c1a4d9e7f205
Revises: aa7c1e9d4f30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c1a4d9e7f205"
down_revision: str | Sequence[str] | None = "aa7c1e9d4f30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing platform administrators and auditors retain their effective
    # privilege while the labels become unambiguous.
    op.execute("UPDATE users SET role = 'platform_admin' WHERE role = 'admin'")
    op.execute("UPDATE users SET role = 'analyst' WHERE role = 'auditor'")
    op.execute("UPDATE organization_memberships SET role = 'organization_owner' WHERE role = 'owner'")
    op.execute("UPDATE organization_memberships SET role = 'analyst' WHERE role = 'member'")
    op.alter_column("users", "role", existing_type=sa.String(length=20), type_=sa.String(length=32), server_default="analyst")
    op.alter_column("organization_memberships", "role", existing_type=sa.String(length=20), type_=sa.String(length=32), server_default="analyst")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'platform_admin'")
    op.execute("UPDATE users SET role = 'auditor' WHERE role IN ('organization_owner', 'analyst')")
    op.execute("UPDATE organization_memberships SET role = 'owner' WHERE role = 'organization_owner'")
    op.execute("UPDATE organization_memberships SET role = 'member' WHERE role = 'analyst'")
    op.alter_column("users", "role", existing_type=sa.String(length=32), type_=sa.String(length=20), server_default="auditor")
    op.alter_column("organization_memberships", "role", existing_type=sa.String(length=32), type_=sa.String(length=20), server_default="member")
