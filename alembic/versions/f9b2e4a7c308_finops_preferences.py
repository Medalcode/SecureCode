"""add persisted FinOps preferences

Revision ID: f9b2e4a7c308
Revises: e8a1d3c6f207
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9b2e4a7c308"
down_revision: Union[str, Sequence[str], None] = "e8a1d3c6f207"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_finops_settings",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("budget_clp", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("alert_threshold_pct", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("alert_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_finops_settings")
