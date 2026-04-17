"""Farmer profile service — queries and updates farmer data."""
import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.farmer import Farmer, CropOfInterest

logger = logging.getLogger(__name__)


class FarmerService:
    """Service for farmer profile operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def get_by_phone(self, phone: str) -> Optional[Farmer]:
        """
        Get farmer by phone number.

        Args:
            phone: Farmer's phone number (WhatsApp format)

        Returns:
            Farmer object or None if not found
        """
        try:
            stmt = select(Farmer).where(Farmer.phone == phone)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error looking up farmer by phone={phone}: {e}")
            return None

    async def get_crops(self, farmer_id: int) -> list[str]:
        """
        Get list of crops farmer is interested in.

        Args:
            farmer_id: Farmer's ID

        Returns:
            List of crop slugs (e.g., ["onion", "wheat"])
        """
        try:
            stmt = select(CropOfInterest.crop).where(CropOfInterest.farmer_id == farmer_id)
            result = await self.session.execute(stmt)
            crops = result.scalars().all()
            return list(crops) if crops else []
        except Exception as e:
            logger.error(f"Error fetching crops for farmer_id={farmer_id}: {e}")
            return []

    async def update_subscription_status(self, farmer_id: int, status: str) -> bool:
        """
        Update farmer's subscription status.

        Args:
            farmer_id: Farmer's ID
            status: New status ("active", "inactive", "paused", etc.)

        Returns:
            True if successful
        """
        try:
            stmt = select(Farmer).where(Farmer.id == farmer_id)
            result = await self.session.execute(stmt)
            farmer = result.scalar_one_or_none()

            if not farmer:
                logger.warning(f"Farmer {farmer_id} not found for subscription update")
                return False

            farmer.subscription_status = status
            farmer.updated_at = datetime.now()
            await self.session.commit()

            logger.info(f"✅ Updated subscription status for farmer={farmer_id} status={status}")
            return True

        except Exception as e:
            logger.error(f"Error updating subscription for farmer_id={farmer_id}: {e}")
            await self.session.rollback()
            return False

    async def get_farmer_profile(self, farmer_id: int) -> Optional[dict]:
        """
        Get complete farmer profile (for handler use).

        Args:
            farmer_id: Farmer's ID

        Returns:
            Dict with farmer details or None if not found
        """
        try:
            farmer = await self._get_by_id(farmer_id)
            if not farmer:
                return None

            crops = await self.get_crops(farmer_id)

            return {
                "farmer_id": farmer.id,
                "phone": farmer.phone,
                "name": farmer.name,
                "district": farmer.district,
                "language": farmer.preferred_language or "mr",
                "subscription_status": farmer.subscription_status,
                "onboarding_state": farmer.onboarding_state,
                "crops": crops,
            }
        except Exception as e:
            logger.error(f"Error fetching farmer profile for farmer_id={farmer_id}: {e}")
            return None

    async def _get_by_id(self, farmer_id: int) -> Optional[Farmer]:
        """Internal helper to get farmer by ID."""
        try:
            stmt = select(Farmer).where(Farmer.id == farmer_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error looking up farmer by id={farmer_id}: {e}")
            return None
