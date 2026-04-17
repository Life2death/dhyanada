"""Add age and land_hectares to farmer profile for scheme eligibility.

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-18 14:00:00.000000

Farmer Profile Enhancement (Phase 2 Module 4):
- Add age (integer): For checking scheme age eligibility
- Add land_hectares (numeric): For checking land size eligibility in schemes
- Both fields nullable: Support gradual adoption during onboarding
"""
from alembic import op
import sqlalchemy as sa


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add age and land_hectares columns to farmers table."""

    op.add_column(
        'farmers',
        sa.Column('age', sa.Integer(), nullable=True),
    )

    op.add_column(
        'farmers',
        sa.Column('land_hectares', sa.Numeric(precision=8, scale=2), nullable=True),
    )

    # Create indexes for eligibility queries
    op.create_index('idx_farmers_age', 'farmers', ['age'])
    op.create_index('idx_farmers_land_hectares', 'farmers', ['land_hectares'])


def downgrade() -> None:
    """Remove age and land_hectares columns from farmers table."""

    op.drop_index('idx_farmers_land_hectares', table_name='farmers')
    op.drop_index('idx_farmers_age', table_name='farmers')

    op.drop_column('farmers', 'land_hectares')
    op.drop_column('farmers', 'age')
