"""Create weather_observations table for Phase 2 weather integration

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weather_observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("apmc", sa.String(100), nullable=False),
        sa.Column("district", sa.String(50), nullable=False),
        sa.Column("taluka", sa.String(100), nullable=False, server_default=""),
        sa.Column("metric", sa.String(50), nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("min_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("forecast_days_ahead", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("condition", sa.String(50), nullable=True),
        sa.Column("advisory", sa.String(500), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("raw_payload", JSONB(none_as_null=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "date", "apmc", "metric", "forecast_days_ahead", "source",
            name="uq_weather_obs_dedupe",
        ),
    )

    op.create_index("idx_weather_lookup", "weather_observations", ["date", "apmc", "forecast_days_ahead"])
    op.create_index("idx_weather_metric", "weather_observations", ["metric", "date"])
    op.create_index("idx_weather_district", "weather_observations", ["district", "date"])
    op.create_index("idx_weather_taluka", "weather_observations", ["taluka", "date"])
    op.create_index("idx_weather_source", "weather_observations", ["source", "fetched_at"])


def downgrade() -> None:
    op.drop_index("idx_weather_source", table_name="weather_observations")
    op.drop_index("idx_weather_taluka", table_name="weather_observations")
    op.drop_index("idx_weather_district", table_name="weather_observations")
    op.drop_index("idx_weather_metric", table_name="weather_observations")
    op.drop_index("idx_weather_lookup", table_name="weather_observations")
    op.drop_table("weather_observations")
