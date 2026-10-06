"""rule traceability

Revision ID: 4d932f877ae7
Revises: 7409c81f5bf7
Create Date: 2026-10-05 23:24:24.127567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d932f877ae7'
down_revision: Union[str, Sequence[str], None] = '7409c81f5bf7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('evaluation_records', sa.Column('rule_id', sa.String(length=100), nullable=True))
    op.add_column('evaluation_records', sa.Column('rule_version', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('evaluation_records', 'rule_version')
    op.drop_column('evaluation_records', 'rule_id')
