"""auth

Revision ID: 1bfdcaee6d14
Revises: 4d932f877ae7
Create Date: 2026-10-05 23:42:35.644209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1bfdcaee6d14'
down_revision: Union[str, Sequence[str], None] = '4d932f877ae7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    op.add_column('evaluation_records', sa.Column('requested_by_user_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_evaluation_user', 'evaluation_records', 'users', ['requested_by_user_id'], ['id'])

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_evaluation_user', 'evaluation_records', type_='foreignkey')
    op.drop_column('evaluation_records', 'requested_by_user_id')
    op.drop_table('users')
