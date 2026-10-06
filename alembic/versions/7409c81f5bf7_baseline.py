"""baseline

Revision ID: 7409c81f5bf7
Revises: 
Create Date: 2026-10-05 23:23:27.672799

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7409c81f5bf7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects.postgresql import JSONB

def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'evidence_records',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('control_id', sa.String(length=50), nullable=False),
        sa.Column('evidence_hash', sa.String(length=64), nullable=False),
        sa.Column('raw_evidence', JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'evaluation_records',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('control_id', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_id', sa.Uuid(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_repository', sa.String(length=255), nullable=False),
        sa.Column('source_branch', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence_records.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('evaluation_records')
    op.drop_table('evidence_records')
