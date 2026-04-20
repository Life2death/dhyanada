"""Global error handling middleware for persistent error logging."""
from __future__ import annotations

import logging
import traceback
from datetime import datetime
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that catches and logs all unhandled exceptions.

    Flow:
    1. Intercept request
    2. Call next handler
    3. If exception occurs, log to database via AlertService
    4. Return error response to client
    5. Never let exception propagate uncaught
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and catch exceptions.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response from handler, or error response if exception occurred
        """
        try:
            response = await call_next(request)
            return response

        except Exception as exc:
            # Extract context from request
            error_context = {
                "path": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.utcnow().isoformat(),
                "query_params": dict(request.query_params) if request.query_params else {},
            }

            # Try to extract farmer_id or phone from headers (if available)
            if "x-farmer-id" in request.headers:
                error_context["farmer_id"] = request.headers["x-farmer-id"]
            if "x-phone" in request.headers:
                error_context["phone"] = request.headers["x-phone"]

            # Determine service from URL path
            if "/webhook/whatsapp" in request.url.path:
                service = "whatsapp"
            elif "/weather" in request.url.path:
                service = "weather"
            elif "/price" in request.url.path:
                service = "price"
            elif "/diagnosis" in request.url.path:
                service = "diagnosis"
            elif "/transcription" in request.url.path:
                service = "transcription"
            else:
                service = "api"

            # Categorize error
            error_type = type(exc).__name__
            if "Timeout" in error_type or "timeout" in str(exc).lower():
                error_type = "timeout"
            elif "API" in error_type or "HTTP" in error_type:
                error_type = "api_error"
            elif "Validation" in error_type or "validation" in str(exc).lower():
                error_type = "validation"
            elif "Database" in error_type or "SQL" in error_type:
                error_type = "database"
            elif "Auth" in error_type or "Unauthorized" in error_type:
                error_type = "auth"
            else:
                error_type = "unknown"

            error_message = str(exc)[:500]
            stacktrace = traceback.format_exc()

            # Log to console immediately (so we see it)
            logger.error(
                f"❌ Unhandled {error_type} in {service}: {error_message}",
                exc_info=True,
            )

            # Try to log to database via AlertService
            try:
                from src.services.alert_service import AlertService
                from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
                from sqlalchemy.orm import sessionmaker
                from src.config import settings

                # Create session for error logging
                engine = create_async_engine(settings.database_url)
                async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

                async with async_session() as session:
                    alert_service = AlertService(session)
                    await alert_service.log_error(
                        service=service,
                        error_type=error_type,
                        message=error_message,
                        stacktrace=stacktrace,
                        context=error_context,
                    )

                await engine.dispose()
            except Exception as db_error:
                # If database logging fails, still log to console
                logger.error(f"Failed to log error to database: {db_error}")

            # Return error response to client
            # Status codes:
            # - 400: Validation error
            # - 401: Auth error
            # - 500: Server error (default)
            if error_type == "validation":
                status_code = 400
            elif error_type == "auth":
                status_code = 401
            elif error_type == "timeout":
                status_code = 504
            else:
                status_code = 500

            return JSONResponse(
                status_code=status_code,
                content={
                    "status": "error",
                    "message": "An error occurred processing your request",
                    "error_type": error_type,
                    # In production, don't expose internal error details
                    # "details": error_message if settings.app_env == "development" else None,
                },
            )
