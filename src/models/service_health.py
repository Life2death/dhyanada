"""Service Health Model for monitoring service status and metrics."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Index

from src.models.base import Base


class ServiceHealth(Base):
    """Real-time health metrics for critical services.

    Updated periodically by health check tasks.
    Used for alerting when services degrade.
    """

    __tablename__ = "service_health"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Service identifier (unique)
    service_name = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Service: whatsapp, weather, price, transcription"
    )

    # Last successful check
    last_heartbeat = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Timestamp of last successful health check"
    )

    # Current health status
    is_healthy = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="True if service is operational, False if degraded"
    )

    # Error rates (for alerting)
    error_rate_1h = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="% errors in last 1 hour (0.0 to 100.0)"
    )

    error_rate_24h = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="% errors in last 24 hours (0.0 to 100.0)"
    )

    # Performance metrics
    avg_latency_ms = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="Average response time in milliseconds"
    )

    # Last update time
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
        comment="When this status was last updated"
    )

    # Additional context
    last_error_message = Column(
        String(500),
        nullable=True,
        comment="Most recent error message (if unhealthy)"
    )

    # Indexes for common queries
    __table_args__ = (
        Index('ix_service_health_status', 'service_name', 'is_healthy'),
        Index('ix_service_health_updated', 'updated_at'),
    )

    def __repr__(self) -> str:
        status = "✅ HEALTHY" if self.is_healthy else "❌ UNHEALTHY"
        return f"<ServiceHealth {self.service_name} {status} error_1h={self.error_rate_1h:.1f}%>"

    def should_alert(self, error_threshold: float = 5.0) -> bool:
        """Determine if this service should trigger an alert.

        Args:
            error_threshold: Alert if error rate exceeds this % (default 5%)

        Returns:
            True if error rate exceeded OR service is marked unhealthy
        """
        return not self.is_healthy or self.error_rate_1h > error_threshold

    def mark_healthy(self, error_rate_1h: float, error_rate_24h: float, avg_latency_ms: float):
        """Mark service as healthy with updated metrics."""
        self.is_healthy = True
        self.error_rate_1h = error_rate_1h
        self.error_rate_24h = error_rate_24h
        self.avg_latency_ms = avg_latency_ms
        self.last_heartbeat = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.last_error_message = None

    def mark_unhealthy(self, error_message: str, error_rate_1h: float = None, error_rate_24h: float = None):
        """Mark service as unhealthy with error details."""
        self.is_healthy = False
        self.last_error_message = error_message[:500]  # Truncate to 500 chars
        if error_rate_1h is not None:
            self.error_rate_1h = error_rate_1h
        if error_rate_24h is not None:
            self.error_rate_24h = error_rate_24h
        self.updated_at = datetime.utcnow()


class ServiceHealthSnapshot:
    """Helper class for service health data transfer (not a model)."""

    def __init__(self, service_name: str, is_healthy: bool, error_rate_1h: float,
                 avg_latency_ms: float, last_heartbeat: datetime):
        self.service_name = service_name
        self.is_healthy = is_healthy
        self.error_rate_1h = error_rate_1h
        self.avg_latency_ms = avg_latency_ms
        self.last_heartbeat = last_heartbeat

    def __repr__(self) -> str:
        status = "HEALTHY" if self.is_healthy else "UNHEALTHY"
        return f"<{self.service_name}: {status}, error={self.error_rate_1h:.1f}%, latency={self.avg_latency_ms:.0f}ms>"
