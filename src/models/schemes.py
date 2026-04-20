"""ORM models for government schemes and MSP alerts."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Date, DateTime, Numeric, String, Text, Boolean, ForeignKey, UUID, func, JSON
from sqlalchemy.orm import relationship

from src.models.base import Base


class GovernmentScheme(Base):
    """Government scheme record (ingested from multiple sources)."""

    __tablename__ = "government_schemes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=func.gen_random_uuid())
    scheme_name = Column(String(200), nullable=False)  # e.g., "PM Kisan Yojana"
    scheme_slug = Column(String(100), nullable=False)  # Canonical slug
    ministry = Column(String(100))
    description = Column(Text)
    eligibility_criteria = Column(JSON)  # {"min_age": 18, "max_land": 5, ...}
    commodities = Column(JSON)  # ["wheat", "rice", ...] as JSON
    min_land_hectares = Column(Numeric(precision=8, scale=2))
    max_land_hectares = Column(Numeric(precision=8, scale=2))
    annual_benefit = Column(String(100))  # "₹6,000/year" or "70% subsidy"
    benefit_amount = Column(Numeric(precision=12, scale=2))
    application_deadline = Column(Date)
    district = Column(String(100), nullable=True)  # NULL = all-India
    state = Column(String(100))
    source = Column(String(50), nullable=False)  # "pmksy_api", "pmfby_api", etc.
    raw_payload = Column(JSON)  # Full API response for audit
    fetched_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<GovernmentScheme {self.scheme_slug} ({self.district or 'all-india'})>"


class MSPAlert(Base):
    """Farmer subscription to MSP (Minimum Support Price) alerts."""

    __tablename__ = "msp_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=func.gen_random_uuid())
    farmer_id = Column(UUID(as_uuid=True), ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False)
    commodity = Column(String(100), nullable=False)  # "onion", "wheat", etc.
    alert_threshold = Column(Numeric(precision=10, scale=2), nullable=False)  # Alert when MSP >= this
    triggered_at = Column(DateTime(timezone=True), nullable=True)  # Last time alert sent
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship to farmer (for convenience)
    farmer = relationship("Farmer", back_populates="msp_alerts")

    def __repr__(self) -> str:
        return f"<MSPAlert farmer={self.farmer_id} commodity={self.commodity} threshold={self.alert_threshold}>"
