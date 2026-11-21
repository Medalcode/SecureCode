"""add csrf token hash to browser sessions

Revision ID: d4e9f1a2b3c4
Revises: a9f3c1e7b205
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e9f1a2b3c4"
down_revision: str | Sequence[str] | None = "a9f3c1e7b205"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_sessions", sa.Column("csrf_token_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("user_sessions", "csrf_token_hash")
