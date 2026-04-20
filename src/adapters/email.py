"""Email Adapter for sending alerts to admin."""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class EmailAdapter:
    """Send email alerts via SMTP (Gmail, custom servers, etc.)."""

    # Alert type colors for HTML formatting
    ALERT_COLORS = {
        "critical": "#dc3545",  # Red
        "warning": "#ffc107",   # Yellow/Orange
        "info": "#17a2b8",      # Blue
        "success": "#28a745",   # Green
    }

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        admin_email: str,
    ):
        """Initialize email adapter with SMTP credentials.

        Args:
            smtp_host: SMTP server hostname (e.g., smtp.gmail.com)
            smtp_port: SMTP port (usually 587 for TLS, 465 for SSL)
            smtp_username: SMTP login username
            smtp_password: SMTP login password
            admin_email: Admin's email address (recipient)
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.admin_email = admin_email
        self.last_alert_time = {}  # Track last alert per service for deduplication

    async def send_alert(
        self,
        subject: str,
        body: str,
        alert_type: str = "info",
        context: Optional[dict] = None,
    ) -> bool:
        """Send email alert to admin.

        Args:
            subject: Email subject line
            body: Plain text body (will be wrapped in HTML)
            alert_type: "critical", "warning", "info", "success" (for color coding)
            context: Optional dict with additional context (service, error_rate, etc.)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Build HTML email
            color = self.ALERT_COLORS.get(alert_type, self.ALERT_COLORS["info"])
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            html_body = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; }}
                        .alert-box {{
                            border-left: 5px solid {color};
                            padding: 15px;
                            background-color: #f8f9fa;
                            margin: 20px 0;
                        }}
                        .alert-type {{
                            color: {color};
                            font-weight: bold;
                            text-transform: uppercase;
                            font-size: 12px;
                        }}
                        .alert-content {{ margin-top: 10px; line-height: 1.6; }}
                        .context-box {{
                            background-color: #fff;
                            border: 1px solid #ddd;
                            padding: 10px;
                            margin-top: 10px;
                            font-size: 12px;
                        }}
                        .footer {{ color: #999; font-size: 11px; margin-top: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="alert-box">
                        <div class="alert-type">[{alert_type.upper()}]</div>
                        <div class="alert-content">{body}</div>
            """

            # Add context if provided
            if context:
                html_body += '<div class="context-box">'
                for key, value in context.items():
                    html_body += f"<strong>{key}:</strong> {value}<br/>"
                html_body += "</div>"

            html_body += f"""
                    </div>
                    <div class="footer">
                        Kisan AI Alert System | {timestamp}
                    </div>
                </body>
            </html>
            """

            # Create MIME message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🚨 [{alert_type.upper()}] {subject}"
            msg["From"] = self.smtp_username
            msg["To"] = self.admin_email

            # Attach plain text and HTML versions
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Send via SMTP
            await asyncio.to_thread(self._send_smtp, msg)
            logger.info(f"✅ Alert sent to {self.admin_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send alert email: {e}", exc_info=True)
            return False

    def _send_smtp(self, msg: MIMEMultipart):
        """Send SMTP message (blocking, called in thread pool).

        Args:
            msg: MIMEMultipart message object
        """
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()  # Use TLS encryption
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)

    async def send_error_alert(
        self,
        service: str,
        error_type: str,
        error_message: str,
        error_count: int,
        alert_type: str = "critical",
    ) -> bool:
        """Send formatted error alert.

        Args:
            service: Service that failed (whatsapp, weather, price, etc.)
            error_type: Error categorization (api_error, timeout, validation)
            error_message: Human-readable error message
            error_count: How many times this error occurred
            alert_type: Alert severity level

        Returns:
            True if sent successfully
        """
        subject = f"{service.upper()} Service Error: {error_type}"
        body = f"""
{error_message}

Service: {service}
Error Type: {error_type}
Occurrences: {error_count}

Please check the admin dashboard for more details.
        """.strip()

        return await self.send_alert(
            subject=subject,
            body=body,
            alert_type=alert_type,
            context={
                "service": service,
                "error_type": error_type,
                "occurrences": error_count,
            },
        )

    async def send_health_alert(
        self,
        service: str,
        is_healthy: bool,
        error_rate_1h: float,
        last_error: Optional[str] = None,
    ) -> bool:
        """Send formatted service health alert.

        Args:
            service: Service name
            is_healthy: True if healthy, False if unhealthy
            error_rate_1h: Error % in last hour
            last_error: Most recent error message

        Returns:
            True if sent successfully
        """
        if is_healthy:
            subject = f"✅ {service.upper()} Service Recovered"
            body = f"{service.upper()} service is back online and healthy."
            alert_type = "success"
        else:
            subject = f"❌ {service.upper()} Service Unhealthy"
            body = f"{service.upper()} service error rate is {error_rate_1h:.1f}% (threshold: 5.0%)"
            if last_error:
                body += f"\n\nLast Error: {last_error}"
            alert_type = "critical"

        return await self.send_alert(
            subject=subject,
            body=body,
            alert_type=alert_type,
            context={
                "service": service,
                "healthy": "Yes" if is_healthy else "No",
                "error_rate_1h": f"{error_rate_1h:.1f}%",
            },
        )

    def should_send_alert(self, service: str, cooldown_minutes: int = 60) -> bool:
        """Check if enough time has passed to send another alert for this service.

        Implements deduplication: don't spam admin with repeated alerts.

        Args:
            service: Service name
            cooldown_minutes: Don't alert again for N minutes (default 60)

        Returns:
            True if should send, False if still in cooldown period
        """
        now = datetime.utcnow()
        last_time = self.last_alert_time.get(service)

        if last_time is None:
            # First alert for this service
            self.last_alert_time[service] = now
            return True

        # Check if cooldown period has elapsed
        elapsed = (now - last_time).total_seconds() / 60  # Convert to minutes
        if elapsed >= cooldown_minutes:
            self.last_alert_time[service] = now
            return True

        return False
