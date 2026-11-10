"""add user lifecycle metadata and administrative audit events

Revision ID: a6e8c5f1d903
Revises: d3e7a1b9c204
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6e8c5f1d903"
down_revision: Union[str, Sequence[str], None] = "d3e7a1b9c204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "user_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_audit_events_target_created", "user_audit_events", ["target_user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_user_audit_events_target_created", table_name="user_audit_events")
    op.drop_table("user_audit_events")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "updated_at")
