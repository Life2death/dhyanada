"""ORM model for generated farmer advisories (Phase 4 Step 3).

One row per (farmer, rule, day) triggered by AdvisoryEngine. Snapshot of
rule text at generation time so subsequent edits don't rewrite history.
"""
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.models.base import Base


class Advisory(Base):
    """A generated, farmer-specific advisory derived from an AdvisoryRule + forecast."""

    __tablename__ = "advisories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farmer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("advisory_rules.id", ondelete="CASCADE"), nullable=False
    )
    crop: Mapped[Optional[str]] = mapped_column(String(50))
    advisory_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)

    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    action_hint: Mapped[str] = mapped_column(String(200), nullable=False)
    source_citation: Mapped[Optional[str]] = mapped_column(String(200))

    delivered_via: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)  # {"dashboard": true, "whatsapp": "msg_id"}
    ai_insights: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)  # AI-generated crop-specific guidance (Phase 1)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("farmer_id", "rule_id", "advisory_date", name="uq_advisory_dedupe"),
        Index("idx_advisory_farmer_date", "farmer_id", "advisory_date"),
        Index("idx_advisory_risk", "risk_level", "advisory_date"),
    )

    def __repr__(self) -> str:
        return f"<Advisory farmer={self.farmer_id} rule={self.rule_id} risk={self.risk_level}>"
