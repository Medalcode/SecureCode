"""add email verification and recovery tokens

Revision ID: e7b1c4d2a809
Revises: c1a4d9e7f205
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "e7b1c4d2a809"
down_revision: str | Sequence[str] | None = "c1a4d9e7f205"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    # Existing accounts were created before email verification existed.  Keep
    # their access unchanged while all future registrations follow the new flow.
    op.execute("UPDATE users SET email_verified_at = created_at WHERE email_verified_at IS NULL")
    op.create_table(
        "account_action_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_account_action_token_hash"),
    )
    op.create_index("ix_account_action_tokens_user_purpose", "account_action_tokens", ["user_id", "purpose"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_account_action_tokens_user_purpose", table_name="account_action_tokens")
    op.drop_table("account_action_tokens")
    op.drop_column("users", "email_verified_at")
