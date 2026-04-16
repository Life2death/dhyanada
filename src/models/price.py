from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Integer, Date, DateTime, Numeric, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.models.base import Base


class MandiPrice(Base):
    __tablename__ = "mandi_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    crop: Mapped[str] = mapped_column(String(50), nullable=False)
    mandi: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str] = mapped_column(String(50), nullable=False)
    modal_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    max_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    msp: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    source: Mapped[str] = mapped_column(String(50), default="agmarknet")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("idx_prices_lookup", "crop", "district", "date"),
        Index("idx_prices_date", "date"),
    )
