"""add revocable user sessions

Revision ID: a9f3c1e7b205
Revises: c3f8a1d6e902
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9f3c1e7b205"
down_revision: str | Sequence[str] | None = "c3f8a1d6e902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti", name="uq_user_sessions_jti"),
    )
    op.create_index("ix_user_sessions_user_active", "user_sessions", ["user_id", "revoked_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_sessions_user_active", table_name="user_sessions")
    op.drop_table("user_sessions")
