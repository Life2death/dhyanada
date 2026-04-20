"""Alert Service for error tracking and threshold-based alerting."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.error_log import ErrorLog
from src.models.service_health import ServiceHealth
from src.adapters.email import EmailAdapter

logger = logging.getLogger(__name__)


class AlertService:
    """Manage error logging and threshold-based alerting.

    Responsibilities:
    - Log errors to database with context
    - Calculate error rates and metrics
    - Check thresholds and trigger email alerts
    - Track which services have been alerted to avoid spam
    """

    def __init__(self, session: AsyncSession, email_adapter: Optional[EmailAdapter] = None):
        """Initialize alert service.

        Args:
            session: Async SQLAlchemy session for database operations
            email_adapter: EmailAdapter for sending alerts (optional)
        """
        self.session = session
        self.email = email_adapter

    async def log_error(
        self,
        service: str,
        error_type: str,
        message: str,
        stacktrace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ErrorLog:
        """Log an error to the database.

        Args:
            service: Service that generated error (whatsapp, weather, price, diagnosis, transcription)
            error_type: Error categorization (api_error, timeout, validation, database, auth, unknown)
            message: Human-readable error message
            stacktrace: Python stacktrace (optional, for debugging)
            context: Contextual data (farmer_id, intent, handler, request_id, etc.)

        Returns:
            Created ErrorLog entry
        """
        error_log = ErrorLog(
            service=service,
            error_type=error_type,
            message=message[:500],  # Truncate to 500 chars
            stacktrace=stacktrace,
            context_json=context or {},
            created_at=datetime.utcnow(),
        )

        self.session.add(error_log)
        await self.session.commit()

        logger.info(
            f"❌ Error logged: service={service}, type={error_type}, msg={message[:100]}"
        )
        return error_log

    async def get_error_rate(self, service: str, hours: int = 1) -> float:
        """Calculate error rate for a service in past N hours.

        Args:
            service: Service name
            hours: Look back this many hours

        Returns:
            Error rate as percentage (0.0 to 100.0)
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Count total errors in period
        error_count = await self.session.scalar(
            select(func.count(ErrorLog.id)).where(
                (ErrorLog.service == service) &
                (ErrorLog.created_at >= cutoff)
            )
        )

        if error_count == 0:
            return 0.0

        # For now, return error count as rate
        # In production, this would be: (error_count / total_requests) * 100
        # But we'd need to track total requests separately
        # For MVP, we'll use a simple threshold: >5 errors in 1h = 10% error rate
        return min(float(error_count * 2), 100.0)  # Simple approximation

    async def get_recent_errors(self, service: str, limit: int = 10) -> list[ErrorLog]:
        """Get recent errors for a service.

        Args:
            service: Service name
            limit: Maximum errors to return

        Returns:
            List of ErrorLog entries, newest first
        """
        result = await self.session.execute(
            select(ErrorLog)
            .where(ErrorLog.service == service)
            .order_by(ErrorLog.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_service_health(
        self,
        service: str,
        is_healthy: bool,
        error_rate_1h: float,
        error_rate_24h: float,
        avg_latency_ms: float,
        error_message: Optional[str] = None,
    ) -> ServiceHealth:
        """Update service health metrics and check thresholds.

        Args:
            service: Service name
            is_healthy: True if service is operational
            error_rate_1h: Error % in last 1 hour
            error_rate_24h: Error % in last 24 hours
            avg_latency_ms: Average response latency
            error_message: Latest error message if unhealthy

        Returns:
            Updated ServiceHealth object
        """
        # Get or create service health record
        result = await self.session.execute(
            select(ServiceHealth).where(ServiceHealth.service_name == service)
        )
        health = result.scalar_one_or_none()

        if not health:
            health = ServiceHealth(
                service_name=service,
                last_heartbeat=datetime.utcnow(),
                is_healthy=is_healthy,
                error_rate_1h=error_rate_1h,
                error_rate_24h=error_rate_24h,
                avg_latency_ms=avg_latency_ms,
            )
            self.session.add(health)
        else:
            # Update existing record
            if is_healthy:
                health.mark_healthy(error_rate_1h, error_rate_24h, avg_latency_ms)
            else:
                health.mark_unhealthy(error_message or "Unknown error", error_rate_1h, error_rate_24h)

        await self.session.commit()

        # Check if we should send alert
        if self.email and health.should_alert(error_threshold=5.0):
            if self.email.should_send_alert(service, cooldown_minutes=60):
                await self.email.send_health_alert(
                    service=service,
                    is_healthy=is_healthy,
                    error_rate_1h=error_rate_1h,
                    last_error=error_message,
                )

        return health

    async def check_all_services(self, error_threshold: float = 5.0) -> list[ServiceHealth]:
        """Get all services and check which need alerts.

        Args:
            error_threshold: Alert if error rate exceeds this %

        Returns:
            List of all ServiceHealth records
        """
        result = await self.session.execute(select(ServiceHealth))
        services = result.scalars().all()

        alerts = [s for s in services if s.should_alert(error_threshold)]
        if alerts:
            logger.warning(
                f"⚠️  {len(alerts)} services need attention: {[s.service_name for s in alerts]}"
            )

        return services

    async def get_error_summary(self, hours: int = 24, service: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of errors in past N hours.

        Args:
            hours: Look back this many hours
            service: Filter by service (optional)

        Returns:
            Dict with error counts by type
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        query = select(
            ErrorLog.service,
            ErrorLog.error_type,
            func.count(ErrorLog.id).label("count")
        ).where(ErrorLog.created_at >= cutoff)

        if service:
            query = query.where(ErrorLog.service == service)

        query = query.group_by(ErrorLog.service, ErrorLog.error_type)

        result = await self.session.execute(query)
        rows = result.all()

        summary = {
            "period_hours": hours,
            "cutoff_time": cutoff.isoformat(),
            "total_errors": sum(row[2] for row in rows),
            "by_service": {},
        }

        for service_name, error_type, count in rows:
            if service_name not in summary["by_service"]:
                summary["by_service"][service_name] = {}
            summary["by_service"][service_name][error_type] = count

        return summary

    async def cleanup_old_errors(self, retention_days: int = 90) -> int:
        """Delete errors older than retention period.

        Args:
            retention_days: Keep errors newer than this many days

        Returns:
            Number of errors deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        result = await self.session.execute(
            select(func.count(ErrorLog.id)).where(ErrorLog.created_at < cutoff)
        )
        count = result.scalar()

        await self.session.execute(
            __import__("sqlalchemy").delete(ErrorLog).where(ErrorLog.created_at < cutoff)
        )
        await self.session.commit()

        logger.info(f"🧹 Cleaned up {count} error logs older than {retention_days} days")
        return count
