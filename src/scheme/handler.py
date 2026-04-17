"""Handler for government scheme queries."""
import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.classifier.intents import IntentResult
from src.scheme.formatter import (
    format_msp_alert_subscription,
    format_msp_alert_triggered,
    format_no_schemes_reply,
    format_schemes_reply,
)
from src.scheme.repository import SchemeRepository

logger = logging.getLogger(__name__)


class SchemeHandler:
    """Handle government scheme queries."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.repo = SchemeRepository(session)

    async def handle_scheme_query(
        self,
        farmer_age: int,
        farmer_land_hectares: float,
        farmer_crops: list[str],
        farmer_district: str,
        farmer_language: str = "mr",
    ) -> str:
        """
        Handle SCHEME_QUERY intent.

        Args:
            farmer_age: Farmer's age
            farmer_land_hectares: Land size
            farmer_crops: List of crops grown
            farmer_district: District (canonical slug)
            farmer_language: "mr" or "en"

        Returns:
            Formatted message with eligible schemes
        """
        try:
            logger.info(
                f"🔍 Scheme query: age={farmer_age}, land={farmer_land_hectares}ha, "
                f"crops={farmer_crops}, district={farmer_district}"
            )

            # Query eligible schemes
            schemes = await self.repo.get_eligible_schemes(
                farmer_age=farmer_age,
                farmer_land_hectares=farmer_land_hectares,
                farmer_crops=farmer_crops,
                farmer_district=farmer_district,
            )

            if not schemes:
                logger.info("❌ No eligible schemes found")
                return format_no_schemes_reply(lang=farmer_language)

            # Format reply
            reply = format_schemes_reply(schemes, lang=farmer_language)
            logger.info(f"✅ Found {len(schemes)} eligible schemes")
            return reply

        except Exception as e:
            logger.error(f"❌ Scheme query failed: {e}")
            return format_no_schemes_reply(lang=farmer_language)

    async def handle_msp_alert(
        self,
        farmer_id: str,
        commodity: str,
        alert_threshold: float,
        farmer_language: str = "mr",
    ) -> str:
        """
        Handle MSP_ALERT intent (subscription).

        Args:
            farmer_id: Farmer's ID (phone)
            commodity: Commodity name (e.g., "onion")
            alert_threshold: Price threshold in ₹
            farmer_language: "mr" or "en"

        Returns:
            Confirmation message
        """
        try:
            logger.info(f"🔔 MSP alert request: {farmer_id} for {commodity} at ₹{alert_threshold}")

            # Save subscription
            success = await self.repo.save_msp_alert(
                farmer_id=farmer_id,
                commodity=commodity,
                alert_threshold=Decimal(str(alert_threshold)),
            )

            if not success:
                logger.error("Failed to save MSP alert")
                return "❌ Failed to set alert. Please try again."

            # Return confirmation
            reply = format_msp_alert_subscription(commodity, alert_threshold, lang=farmer_language)
            logger.info(f"✅ MSP alert subscribed: {farmer_id} for {commodity}")
            return reply

        except Exception as e:
            logger.error(f"❌ MSP alert subscription failed: {e}")
            return "❌ Failed to set alert. Please try again."
