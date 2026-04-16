"""Initial schema — all 6 tables

Revision ID: 0001
Revises:
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farmers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(100)),
        sa.Column("district", sa.String(50)),
        sa.Column("preferred_language", sa.String(10), server_default="mr"),
        sa.Column("plan_tier", sa.String(20), server_default="free"),
        sa.Column("subscription_status", sa.String(20), server_default="none"),
        sa.Column("onboarding_state", sa.String(30), server_default="new"),
        sa.Column("queries_today", sa.Integer(), server_default="0"),
        sa.Column("queries_reset_at", sa.DateTime(timezone=True)),
        sa.Column("consent_given_at", sa.DateTime(timezone=True)),
        sa.Column("consent_version", sa.String(10)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_farmers_phone", "farmers", ["phone"])
    op.create_index("idx_farmers_district", "farmers", ["district"])

    op.create_table(
        "crops_of_interest",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("farmers.id", ondelete="CASCADE")),
        sa.Column("crop", sa.String(50), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_crops_farmer", "crops_of_interest", ["farmer_id"])

    op.create_table(
        "mandi_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("crop", sa.String(50), nullable=False),
        sa.Column("mandi", sa.String(100), nullable=False),
        sa.Column("district", sa.String(50), nullable=False),
        sa.Column("modal_price", sa.Numeric(10, 2)),
        sa.Column("min_price", sa.Numeric(10, 2)),
        sa.Column("max_price", sa.Numeric(10, 2)),
        sa.Column("msp", sa.Numeric(10, 2)),
        sa.Column("source", sa.String(50), server_default="agmarknet"),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("is_stale", sa.Boolean(), server_default="false"),
    )
    op.create_index("idx_prices_lookup", "mandi_prices", ["crop", "district", "date"])
    op.create_index("idx_prices_date", "mandi_prices", ["date"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("farmers.id")),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("message_type", sa.String(20), nullable=False),
        sa.Column("raw_message", sa.Text()),
        sa.Column("detected_intent", sa.String(50)),
        sa.Column("detected_entities", postgresql.JSONB()),
        sa.Column("response_sent", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_conv_farmer", "conversations", ["farmer_id"])
    op.create_index("idx_conv_created", "conversations", ["created_at"])

    op.create_table(
        "broadcast_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("farmers.id")),
        sa.Column("template_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("cost_paise", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_broadcast_farmer", "broadcast_log", ["farmer_id"])
    op.create_index("idx_broadcast_status", "broadcast_log", ["status"])

    op.create_table(
        "consent_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("farmers.id")),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("consent_version", sa.String(10)),
        sa.Column("message_id", sa.String(100)),
        sa.Column("ip_address", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_consent_farmer", "consent_events", ["farmer_id"])


def downgrade() -> None:
    op.drop_table("consent_events")
    op.drop_table("broadcast_log")
    op.drop_table("conversations")
    op.drop_table("mandi_prices")
    op.drop_table("crops_of_interest")
    op.drop_table("farmers")
