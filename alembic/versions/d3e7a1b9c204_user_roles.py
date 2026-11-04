"""add user roles

Revision ID: d3e7a1b9c204
Revises: 1bfdcaee6d14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3e7a1b9c204"
down_revision: Union[str, Sequence[str], None] = "1bfdcaee6d14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing accounts retain least privilege after upgrade.
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="auditor"),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
