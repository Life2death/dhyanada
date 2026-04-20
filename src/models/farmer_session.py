"""Farmer session model for OTP-based authentication."""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.models.base import Base


class FarmerSession(Base):
    """Track farmer login sessions with OTP verification."""

    __tablename__ = "farmer_sessions"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)
    phone = Column(String(20), nullable=False)  # Phone number for reference
    session_token = Column(String(128), unique=True, nullable=False, index=True)
    otp = Column(String(6), nullable=False)  # 6-digit OTP
    otp_expires_at = Column(DateTime, nullable=False)  # OTP valid for 10 minutes
    verified_at = Column(DateTime, nullable=True)  # When OTP was verified
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # Session valid for 24 hours

    # Relationship
    farmer = relationship("Farmer", back_populates="sessions")

    # Indexes
    __table_args__ = (
        Index("idx_farmer_session_farmer_id", "farmer_id"),
        Index("idx_farmer_session_token", "session_token"),
        Index("idx_farmer_session_expires", "expires_at"),
    )

    def is_valid(self) -> bool:
        """Check if session is still valid."""
        return datetime.utcnow() < self.expires_at and self.verified_at is not None

    def is_otp_valid(self) -> bool:
        """Check if OTP is still valid (not expired)."""
        return datetime.utcnow() < self.otp_expires_at and self.verified_at is None

    @staticmethod
    def generate_session_token() -> str:
        """Generate a random session token (used for JWT)."""
        import secrets
        return secrets.token_urlsafe(96)

    @staticmethod
    def generate_otp() -> str:
        """Generate a random 6-digit OTP."""
        import random
        return "".join(str(random.randint(0, 9)) for _ in range(6))

    def __repr__(self) -> str:
        return f"<FarmerSession(id={self.id}, farmer_id={self.farmer_id}, phone={self.phone})>"
