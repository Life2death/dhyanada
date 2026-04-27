"""Add taluka and village_id to farmers table.

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('farmers', sa.Column('taluka', sa.String(100), nullable=True))
    op.add_column(
        'farmers',
        sa.Column('village_id', sa.Integer(), sa.ForeignKey('villages.id'), nullable=True),
    )
    op.create_index('idx_farmers_village', 'farmers', ['village_id'])


def downgrade() -> None:
    op.drop_index('idx_farmers_village', table_name='farmers')
    op.drop_column('farmers', 'village_id')
    op.drop_column('farmers', 'taluka')
