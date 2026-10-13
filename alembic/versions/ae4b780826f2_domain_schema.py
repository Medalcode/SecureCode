"""add controls, rules, sources tables + indices + tenant_id columns

Revision ID: ae4b780826f2
Revises: 1bfdcaee6d14
Create Date: 2026-10-07 02:44:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'ae4b780826f2'
down_revision: Union[str, Sequence[str], None] = '1bfdcaee6d14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Orden de ejecución:
      1. controls  (sin dependencias externas)
      2. rules     (FK → controls.control_id)
      3. sources   (sin dependencias externas)
      4. ADD COLUMN tenant_id a evidence_records
      5. ADD COLUMN tenant_id a evaluation_records
      6. Índices faltantes en evidence_records  (incluye UNIQUE con tenant_id)
      7. Índices faltantes en evaluation_records
    """

    # ------------------------------------------------------------------
    # 1. Tabla controls — catálogo maestro de controles GRC
    # ------------------------------------------------------------------
    op.create_table(
        'controls',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('control_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False,
                  server_default='GitHub'),
        sa.Column('active', sa.Boolean(), nullable=False,
                  server_default=sa.text('TRUE')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('control_id', name='uq_controls_control_id'),
    )
    op.create_index('idx_controls_control_id',  'controls', ['control_id'])
    op.create_index('idx_controls_source_type', 'controls', ['source_type'])
    op.create_index('idx_controls_active',      'controls', ['active'])
    op.create_index('idx_controls_tenant_id',   'controls', ['tenant_id'])

    # ------------------------------------------------------------------
    # 2. Tabla rules — historial versionado de RuleDefinition
    #    FK → controls.control_id ON UPDATE CASCADE ON DELETE RESTRICT
    # ------------------------------------------------------------------
    op.create_table(
        'rules',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('rule_id', sa.String(length=100), nullable=False),
        sa.Column('control_id', sa.String(length=50), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False,
                  server_default=sa.text('TRUE')),
        sa.Column('condition', JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('allowlisted_fields', JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_id', 'version', name='uq_rules_rule_version'),
        sa.ForeignKeyConstraint(
            ['control_id'], ['controls.control_id'],
            name='fk_rules_control_id',
            onupdate='CASCADE',
            ondelete='RESTRICT',
        ),
    )
    op.create_index('idx_rules_control_id', 'rules', ['control_id'])
    op.create_index('idx_rules_rule_id',    'rules', ['rule_id'])
    op.create_index('idx_rules_active',     'rules', ['active'])
    op.create_index('idx_rules_tenant_id',  'rules', ['tenant_id'])

    # ------------------------------------------------------------------
    # 3. Tabla sources — conexiones reutilizables a fuentes de evidencia
    # ------------------------------------------------------------------
    op.create_table(
        'sources',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False,
                  server_default='GitHub'),
        sa.Column('owner', sa.String(length=255), nullable=False),
        sa.Column('repository', sa.String(length=255), nullable=False),
        sa.Column('default_branch', sa.String(length=255), nullable=False,
                  server_default='main'),
        sa.Column('active', sa.Boolean(), nullable=False,
                  server_default=sa.text('TRUE')),
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'source_type', 'owner', 'repository', 'tenant_id',
            name='uq_sources_repo_tenant',
        ),
    )
    op.create_index('idx_sources_owner_repo',  'sources', ['owner', 'repository'])
    op.create_index('idx_sources_source_type', 'sources', ['source_type'])
    op.create_index('idx_sources_active',      'sources', ['active'])
    op.create_index('idx_sources_tenant_id',   'sources', ['tenant_id'])

    # ------------------------------------------------------------------
    # 4. ADD COLUMN tenant_id → evidence_records
    #    O(1) en PostgreSQL moderno: no reescribe filas, solo actualiza catálogo.
    #    DEFAULT NULL → todos los registros legacy quedan como tenant global.
    # ------------------------------------------------------------------
    op.add_column('evidence_records',
                  sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_index('idx_evidence_tenant_id', 'evidence_records', ['tenant_id'])

    # ------------------------------------------------------------------
    # 5. ADD COLUMN tenant_id → evaluation_records
    # ------------------------------------------------------------------
    op.add_column('evaluation_records',
                  sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_index('idx_eval_tenant_id', 'evaluation_records', ['tenant_id'])

    # ------------------------------------------------------------------
    # 6. Índices faltantes en evidence_records
    #    UNIQUE incluye tenant_id: dos tenants distintos pueden tener la misma
    #    (control_id, evidence_hash). NULLs son distintos en B-tree → compatible
    #    con todos los registros legacy (tenant_id=NULL).
    # ------------------------------------------------------------------
    op.create_index(
        'uq_evidence_control_hash', 'evidence_records',
        ['control_id', 'evidence_hash', 'tenant_id'],
        unique=True,
    )
    op.create_index('idx_evidence_control_id',   'evidence_records', ['control_id'])
    op.create_index('idx_evidence_collected_at', 'evidence_records', ['collected_at'])

    # ------------------------------------------------------------------
    # 7. Índices faltantes en evaluation_records
    # ------------------------------------------------------------------
    op.create_index('idx_eval_control_id',   'evaluation_records', ['control_id'])
    op.create_index('idx_eval_status',       'evaluation_records', ['status'])
    op.create_index('idx_eval_evaluated_at', 'evaluation_records', ['evaluated_at'])
    op.create_index('idx_eval_source_repo',  'evaluation_records', ['source_repository'])
    op.create_index('idx_eval_rule_id',      'evaluation_records', ['rule_id'])


def downgrade() -> None:
    """Downgrade schema — orden inverso estricto al upgrade."""

    # 7 — Quitar índices de evaluation_records
    op.drop_index('idx_eval_rule_id',      table_name='evaluation_records')
    op.drop_index('idx_eval_source_repo',  table_name='evaluation_records')
    op.drop_index('idx_eval_evaluated_at', table_name='evaluation_records')
    op.drop_index('idx_eval_status',       table_name='evaluation_records')
    op.drop_index('idx_eval_control_id',   table_name='evaluation_records')
    op.drop_index('idx_eval_tenant_id',    table_name='evaluation_records')
    op.drop_column('evaluation_records', 'tenant_id')

    # 6 — Quitar índices de evidence_records
    op.drop_index('uq_evidence_control_hash',  table_name='evidence_records')
    op.drop_index('idx_evidence_collected_at', table_name='evidence_records')
    op.drop_index('idx_evidence_control_id',   table_name='evidence_records')
    op.drop_index('idx_evidence_tenant_id',    table_name='evidence_records')
    op.drop_column('evidence_records', 'tenant_id')

    # 5-3 — Eliminar tablas nuevas (rules antes que controls por FK)
    op.drop_table('sources')
    op.drop_table('rules')
    op.drop_table('controls')
