"""add persisted client settings

Revision ID: c7f9a2e4b105
Revises: a6e8c5f1d903
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7f9a2e4b105"
down_revision: Union[str, Sequence[str], None] = "a6e8c5f1d903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("default_repository", sa.String(length=200), nullable=True),
        sa.Column("default_branch", sa.String(length=255), nullable=False, server_default="main"),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="es-CL"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="America/Santiago"),
        sa.Column("theme", sa.String(length=16), nullable=False, server_default="system"),
        sa.Column("notify_evaluation_completed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_evaluation_failure", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_weekly_digest", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
