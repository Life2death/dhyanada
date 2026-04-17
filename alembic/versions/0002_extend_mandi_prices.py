"""Extend mandi_prices for multi-source ingestion

Adds:
- variety (text) — e.g. "Local", "Pimpalgaon", "Medium Staple"
- apmc (text) — canonical APMC code (e.g. "vashi", "lasalgaon")
- arrival_quantity_qtl (numeric) — daily arrival tonnage in quintals
- raw_payload (JSONB) — original source record for debugging/replay
- UNIQUE (date, apmc, crop, variety, source) — dedupe key for merge pipeline

Source values now include: 'agmarknet' | 'msamb' | 'nhrdf' | 'vashi'

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mandi_prices",
        sa.Column("variety", sa.String(100), nullable=True),
    )
    op.add_column(
        "mandi_prices",
        sa.Column("apmc", sa.String(100), nullable=True),
    )
    op.add_column(
        "mandi_prices",
        sa.Column("arrival_quantity_qtl", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "mandi_prices",
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
    )

    # Backfill apmc from mandi for any existing rows
    op.execute("UPDATE mandi_prices SET apmc = LOWER(REPLACE(mandi, ' ', '_')) WHERE apmc IS NULL")

    op.create_unique_constraint(
        "uq_mandi_prices_dedupe",
        "mandi_prices",
        ["date", "apmc", "crop", "variety", "source"],
    )
    op.create_index(
        "idx_mandi_prices_commodity_date",
        "mandi_prices",
        ["crop", "date"],
    )
    op.create_index(
        "idx_mandi_prices_district_date",
        "mandi_prices",
        ["district", "date"],
    )


def downgrade() -> None:
    op.drop_index("idx_mandi_prices_district_date", table_name="mandi_prices")
    op.drop_index("idx_mandi_prices_commodity_date", table_name="mandi_prices")
    op.drop_constraint("uq_mandi_prices_dedupe", "mandi_prices", type_="unique")
    op.drop_column("mandi_prices", "raw_payload")
    op.drop_column("mandi_prices", "arrival_quantity_qtl")
    op.drop_column("mandi_prices", "apmc")
    op.drop_column("mandi_prices", "variety")
