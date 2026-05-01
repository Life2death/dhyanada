"""Add ai_insights field to advisory model.

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-01 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ai_insights field to advisories table
    op.add_column('advisories', sa.Column('ai_insights', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('advisories', 'ai_insights')
