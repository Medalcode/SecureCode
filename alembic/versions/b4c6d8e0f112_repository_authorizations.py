"""add per-user repository authorizations

Revision ID: b4c6d8e0f112
Revises: f9b2e4a7c308
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c6d8e0f112"
down_revision: Union[str, Sequence[str], None] = "f9b2e4a7c308"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repository_authorizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("repository", sa.String(length=201), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "repository", name="uq_repository_authorization_user_repository"),
    )
    op.create_index("ix_repository_authorizations_user_active", "repository_authorizations", ["user_id", "active"])


def downgrade() -> None:
    op.drop_index("ix_repository_authorizations_user_active", table_name="repository_authorizations")
    op.drop_table("repository_authorizations")
