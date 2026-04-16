from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.models.base import Base


class ConsentEvent(Base):
    __tablename__ = "consent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farmer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("farmers.id"))
    # opt_in | opt_out | erasure_request | erasure_complete
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    consent_version: Mapped[Optional[str]] = mapped_column(String(10))
    message_id: Mapped[Optional[str]] = mapped_column(String(100))
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_consent_farmer", "farmer_id"),)
