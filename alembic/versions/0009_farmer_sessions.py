"""Create farmer_sessions table for OTP-based authentication.

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-18 17:00:00.000000

Phase 4 Step 1 - Custom Farmer Dashboards:
- Create farmer_sessions table for OTP authentication
- Track session tokens, OTP codes, and expiration times
- Support farmer login via phone number + OTP
"""
from alembic import op
import sqlalchemy as sa


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create farmer_sessions table for OTP-based authentication."""

    op.create_table(
        'farmer_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('farmer_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('session_token', sa.String(length=128), nullable=False),
        sa.Column('otp', sa.String(length=6), nullable=False),
        sa.Column('otp_expires_at', sa.DateTime(), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for fast queries
    op.create_index('idx_farmer_session_farmer_id', 'farmer_sessions', ['farmer_id'])
    op.create_index('idx_farmer_session_token', 'farmer_sessions', ['session_token'], unique=True)
    op.create_index('idx_farmer_session_expires', 'farmer_sessions', ['expires_at'])


def downgrade() -> None:
    """Remove farmer_sessions table."""

    op.drop_index('idx_farmer_session_expires', table_name='farmer_sessions')
    op.drop_index('idx_farmer_session_token', table_name='farmer_sessions')
    op.drop_index('idx_farmer_session_farmer_id', table_name='farmer_sessions')

    op.drop_table('farmer_sessions')
