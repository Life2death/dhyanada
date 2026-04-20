"""ORM model for admin-managed advisory rules (Phase 4 Step 3).

A rule is a weather-threshold template that, when matched against a farmer's
forecast + crops + district, produces an Advisory. Rules are editable by admins.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.models.base import Base


class AdvisoryRule(Base):
    """A single condition-threshold rule evaluated nightly against each farmer's forecast."""

    __tablename__ = "advisory_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    advisory_type: Mapped[str] = mapped_column(String(30), nullable=False)  # disease | irrigation | weather | pest
    crop: Mapped[Optional[str]] = mapped_column(String(50))  # NULL = all crops

    eligible_districts: Mapped[Optional[list[str]]] = mapped_column(JSON)  # ["pune", "nashik"]; NULL = all India

    # Weather thresholds (any NULL = not checked)
    min_temp_c: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    max_temp_c: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    min_humidity_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    max_humidity_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    min_rainfall_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    max_rainfall_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    consecutive_days: Mapped[int] = mapped_column(Integer, default=1)

    # Output
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)  # low | medium | high
    title_en: Mapped[str] = mapped_column(String(120), nullable=False)
    message_en: Mapped[str] = mapped_column(String(500), nullable=False)
    message_mr: Mapped[Optional[str]] = mapped_column(String(500))
    action_hint: Mapped[str] = mapped_column(String(200), nullable=False)
    source_citation: Mapped[Optional[str]] = mapped_column(String(200))

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_advisory_rule_type", "advisory_type", "active"),
        Index("idx_advisory_rule_crop", "crop", "active"),
    )

    def __repr__(self) -> str:
        return f"<AdvisoryRule {self.rule_key} ({self.advisory_type}, {self.risk_level})>"
