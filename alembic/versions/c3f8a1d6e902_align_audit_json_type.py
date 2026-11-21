"""align audit event JSON type with SQLAlchemy metadata

Revision ID: c3f8a1d6e902
Revises: b7e4a2c9d615
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c3f8a1d6e902"
down_revision: str | Sequence[str] | None = "b7e4a2c9d615"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.alter_column(
        "user_audit_events",
        "details",
        existing_type=sa.JSON(),
        type_=postgresql.JSONB(),
        existing_nullable=False,
        postgresql_using="details::jsonb",
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.alter_column(
        "user_audit_events",
        "details",
        existing_type=postgresql.JSONB(),
        type_=sa.JSON(),
        existing_nullable=False,
        postgresql_using="details::json",
    )
