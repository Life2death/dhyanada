"""Split farmer.name into first_name + last_name.

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('farmers', sa.Column('first_name', sa.String(50), nullable=True))
    op.add_column('farmers', sa.Column('last_name', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('farmers', 'last_name')
    op.drop_column('farmers', 'first_name')
