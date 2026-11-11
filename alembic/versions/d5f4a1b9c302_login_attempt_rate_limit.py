"""add durable login-attempt throttle state

Revision ID: d5f4a1b9c302
Revises: b4c6d8e0f112
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5f4a1b9c302"
down_revision: Union[str, Sequence[str], None] = "b4c6d8e0f112"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("scope_hash", sa.String(length=64), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("scope_hash"),
    )


def downgrade() -> None:
    op.drop_table("login_attempts")
