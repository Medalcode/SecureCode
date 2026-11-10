"""add user subscription lifecycle

Revision ID: e8a1d3c6f207
Revises: c7f9a2e4b105
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8a1d3c6f207"
down_revision: Union[str, Sequence[str], None] = "c7f9a2e4b105"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_subscriptions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.String(length=32), nullable=False, server_default="pro"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "subscription_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("previous_plan_id", sa.String(length=32), nullable=True),
        sa.Column("new_plan_id", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscription_events_user_occurred", "subscription_events", ["user_id", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_subscription_events_user_occurred", table_name="subscription_events")
    op.drop_table("subscription_events")
    op.drop_table("user_subscriptions")
