"""Error Log Model for persistent error tracking."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index, ForeignKey
from sqlalchemy.orm import relationship

from src.models.base import Base


class ErrorLog(Base):
    """Persistent error logging for all system failures.

    Tracks:
    - Unhandled exceptions from middleware
    - API failures (WhatsApp, Weather, Price, Transcription)
    - Business logic errors (validation, timeouts, etc.)
    - Error categorization for trends analysis
    """

    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Service that generated the error
    service = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Service: whatsapp, weather, price, diagnosis, transcription, unknown"
    )

    # Error categorization for alerting
    error_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: api_error, timeout, validation, database, auth, unknown"
    )

    # Human-readable error message
    message = Column(
        Text,
        nullable=False,
        comment="Error message/description"
    )

    # Full Python stacktrace (for debugging)
    stacktrace = Column(
        Text,
        nullable=True,
        comment="Full stack trace for investigation"
    )

    # Context about the error (farmer_id, intent, handler, request_id)
    context_json = Column(
        JSON,
        nullable=True,
        comment="Context: {farmer_id, intent, handler, request_path, method}"
    )

    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="When error occurred"
    )

    resolved_at = Column(
        DateTime,
        nullable=True,
        comment="When error was resolved (if applicable)"
    )

    # Indexes for common queries
    __table_args__ = (
        Index('ix_error_service_type', 'service', 'error_type'),
        Index('ix_error_created_service', 'created_at', 'service'),
        Index('ix_error_resolved', 'resolved_at'),
    )

    def __repr__(self) -> str:
        return f"<ErrorLog service={self.service} type={self.error_type} created={self.created_at.isoformat()}>"

    def mark_resolved(self):
        """Mark this error as resolved."""
        self.resolved_at = datetime.utcnow()


class ErrorStatistic:
    """Helper class for aggregated error statistics (not a model, just data holder)."""

    def __init__(self, service: str, error_type: str, count: int, latest: datetime):
        self.service = service
        self.error_type = error_type
        self.count = count
        self.latest = latest

    def __repr__(self) -> str:
        return f"<ErrorStatistic {self.service}/{self.error_type}: {self.count} errors>"
