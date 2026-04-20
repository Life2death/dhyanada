"""Create advisory_rules and advisories tables.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-19 10:00:00.000000

Phase 4 Step 3 - Predictive Analytics & Advisory Engine:
- advisory_rules: admin-managed weather-threshold rules
- advisories: generated per-farmer per-day advisories, dedup via UNIQUE
"""
from alembic import op
import sqlalchemy as sa


revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'advisory_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_key', sa.String(length=60), nullable=False),
        sa.Column('advisory_type', sa.String(length=30), nullable=False),
        sa.Column('crop', sa.String(length=50), nullable=True),
        sa.Column('eligible_districts', sa.JSON(), nullable=True),
        sa.Column('min_temp_c', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('max_temp_c', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('min_humidity_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('max_humidity_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('min_rainfall_mm', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('max_rainfall_mm', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('consecutive_days', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('risk_level', sa.String(length=10), nullable=False),
        sa.Column('title_en', sa.String(length=120), nullable=False),
        sa.Column('message_en', sa.String(length=500), nullable=False),
        sa.Column('message_mr', sa.String(length=500), nullable=True),
        sa.Column('action_hint', sa.String(length=200), nullable=False),
        sa.Column('source_citation', sa.String(length=200), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_key'),
    )
    op.create_index('idx_advisory_rule_type', 'advisory_rules', ['advisory_type', 'active'])
    op.create_index('idx_advisory_rule_crop', 'advisory_rules', ['crop', 'active'])

    op.create_table(
        'advisories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('farmer_id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('crop', sa.String(length=50), nullable=True),
        sa.Column('advisory_date', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=False),
        sa.Column('risk_level', sa.String(length=10), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=False),
        sa.Column('action_hint', sa.String(length=200), nullable=False),
        sa.Column('source_citation', sa.String(length=200), nullable=True),
        sa.Column('delivered_via', sa.JSON(), nullable=True),
        sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['advisory_rules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('farmer_id', 'rule_id', 'advisory_date', name='uq_advisory_dedupe'),
    )
    op.create_index('idx_advisory_farmer_date', 'advisories', ['farmer_id', 'advisory_date'])
    op.create_index('idx_advisory_risk', 'advisories', ['risk_level', 'advisory_date'])


def downgrade() -> None:
    op.drop_index('idx_advisory_risk', table_name='advisories')
    op.drop_index('idx_advisory_farmer_date', table_name='advisories')
    op.drop_table('advisories')

    op.drop_index('idx_advisory_rule_crop', table_name='advisory_rules')
    op.drop_index('idx_advisory_rule_type', table_name='advisory_rules')
    op.drop_table('advisory_rules')
