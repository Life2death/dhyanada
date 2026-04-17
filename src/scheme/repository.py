"""Repository for scheme queries and MSP alerts."""
import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SchemeRepository:
    """Query government schemes and manage MSP alerts."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def get_eligible_schemes(
        self,
        farmer_age: int,
        farmer_land_hectares: float,
        farmer_crops: list[str],
        farmer_district: Optional[str],
    ) -> list[dict]:
        """
        Get schemes eligible for this farmer.

        Filters by:
        - Age >= min_age in eligibility_criteria
        - Land between min/max_land_hectares
        - Commodity overlap
        - District (NULL = nationwide, or match farmer district)
        - Active (application_deadline >= today)

        Returns:
            List of dicts with scheme details, sorted by benefit (descending)
        """
        try:
            from src.models.schemes import GovernmentScheme

            today = date.today()

            # Build query
            query = select(GovernmentScheme).where(
                and_(
                    # Eligibility criteria check (simplified for now)
                    GovernmentScheme.application_deadline >= today,
                    # District match (NULL = all-India)
                    or_(
                        GovernmentScheme.district == None,
                        GovernmentScheme.district == farmer_district,
                    ),
                    # Land size check
                    GovernmentScheme.min_land_hectares <= farmer_land_hectares,
                    or_(
                        GovernmentScheme.max_land_hectares == None,
                        GovernmentScheme.max_land_hectares >= farmer_land_hectares,
                    ),
                )
            )

            result = await self.session.execute(query)
            schemes = result.scalars().all()

            # Post-filter for commodity overlap and age (can't use JSONB operators easily in filter)
            eligible = []
            for scheme in schemes:
                # Check commodity overlap
                if scheme.commodities:
                    overlap = set(scheme.commodities) & set(farmer_crops)
                    if not overlap and "all" not in scheme.commodities:
                        continue

                # Check age (simplified: assume min_age from eligibility_criteria)
                if scheme.eligibility_criteria:
                    min_age = scheme.eligibility_criteria.get("min_age", 0)
                    if farmer_age < min_age:
                        continue

                eligible.append(
                    {
                        "scheme_name": scheme.scheme_name,
                        "scheme_slug": scheme.scheme_slug,
                        "ministry": scheme.ministry,
                        "annual_benefit": scheme.annual_benefit,
                        "benefit_amount": float(scheme.benefit_amount) if scheme.benefit_amount else 0,
                        "application_deadline": scheme.application_deadline,
                        "description": scheme.description,
                        "eligibility_criteria": scheme.eligibility_criteria,
                        "commodities": scheme.commodities,
                    }
                )

            # Sort by benefit amount (descending)
            eligible.sort(key=lambda x: x["benefit_amount"], reverse=True)
            logger.info(f"✅ Found {len(eligible)} eligible schemes for farmer (age={farmer_age}, land={farmer_land_hectares}ha, crops={farmer_crops})")

            return eligible

        except Exception as e:
            logger.error(f"❌ Failed to query eligible schemes: {e}")
            return []

    async def save_msp_alert(
        self,
        farmer_id: str,
        commodity: str,
        alert_threshold: Decimal,
    ) -> bool:
        """
        Create or update MSP alert subscription.

        Args:
            farmer_id: Farmer's ID
            commodity: Commodity name (e.g., "onion")
            alert_threshold: Alert when MSP >= this value

        Returns:
            True if successful
        """
        try:
            from src.models.schemes import MSPAlert
            from datetime import datetime

            # Upsert: create or update
            stmt = (
                MSPAlert.__table__.insert()
                .values(
                    farmer_id=farmer_id,
                    commodity=commodity,
                    alert_threshold=alert_threshold,
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
                .on_conflict_do_update(
                    index_elements=["farmer_id", "commodity"],
                    set_={
                        "alert_threshold": alert_threshold,
                        "is_active": True,
                    },
                )
            )

            await self.session.execute(stmt)
            await self.session.commit()
            logger.info(f"✅ MSP alert saved: {farmer_id} for {commodity} at ₹{alert_threshold}/qt")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to save MSP alert: {e}")
            await self.session.rollback()
            return False

    async def get_msp_alerts_for_commodity(self, commodity: str) -> list[dict]:
        """
        Get all active MSP alerts for a commodity.

        Used by scheduler to trigger notifications when price is reached.

        Args:
            commodity: Commodity name (e.g., "onion")

        Returns:
            List of alert records (farmer_id, threshold, last_triggered)
        """
        try:
            from src.models.schemes import MSPAlert

            query = select(MSPAlert).where(
                and_(
                    MSPAlert.commodity == commodity,
                    MSPAlert.is_active == True,
                )
            )

            result = await self.session.execute(query)
            alerts = result.scalars().all()

            return [
                {
                    "farmer_id": str(alert.farmer_id),
                    "commodity": alert.commodity,
                    "threshold": float(alert.alert_threshold),
                    "triggered_at": alert.triggered_at,
                }
                for alert in alerts
            ]

        except Exception as e:
            logger.error(f"❌ Failed to get MSP alerts for {commodity}: {e}")
            return []
