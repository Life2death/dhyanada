"""Data repository for farmer dashboard queries."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import json

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.farmer import Farmer, CropOfInterest
from src.models.price import MandiPrice
from src.models.schemes import GovernmentScheme
from src.models.conversation import Conversation
from src.models.weather import WeatherObservation
from src.farmer.models import (
    PriceData,
    WeatherData,
    WeatherForecastDay,
    SchemeData,
    FarmerStats,
    FarmerInfo,
    FarmerDashboardData,
    AdvisoryCard,
)
from src.models.advisory import Advisory
from src.models.advisory_rule import AdvisoryRule


class FarmerRepository:
    """Repository for farmer dashboard data queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_farmer(self, farmer_id: int) -> Optional[Farmer]:
        """Get farmer by ID."""
        stmt = select(Farmer).where(Farmer.id == farmer_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_farmer_crops(self, farmer_id: int) -> List[str]:
        """Get list of crops farmer follows."""
        stmt = (
            select(CropOfInterest.crop)
            .where(CropOfInterest.farmer_id == farmer_id)
            .distinct()
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_crop_prices_30d(
        self, crops: List[str], district: str
    ) -> List[PriceData]:
        """Get 30-day price history for crops in farmer's district."""
        if not crops or not district:
            return []

        prices_data = []
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)

        for crop in crops:
            stmt = (
                select(MandiPrice)
                .where(
                    and_(
                        MandiPrice.crop == crop,
                        MandiPrice.district == district,
                        MandiPrice.date >= thirty_days_ago,
                    )
                )
                .order_by(MandiPrice.date.desc())
            )
            result = await self.db.execute(stmt)
            prices = result.scalars().all()

            if not prices:
                continue

            # Calculate stats
            latest = prices[0]
            modal_prices = [p.modal_price for p in prices if p.modal_price]
            min_prices = [p.min_price for p in prices if p.min_price]
            max_prices = [p.max_price for p in prices if p.max_price]

            latest_price = latest.modal_price
            min_30d = min(min_prices) if min_prices else None
            max_30d = max(max_prices) if max_prices else None
            avg_30d = sum(modal_prices) / len(modal_prices) if modal_prices else None

            # Calculate 7-day price change
            seven_days_ago = datetime.utcnow().date() - timedelta(days=7)
            prices_7d = [p for p in prices if p.date >= seven_days_ago]
            pct_change_7d = 0.0
            if prices_7d and latest_price and avg_30d:
                oldest_7d = prices_7d[-1]
                if oldest_7d.modal_price:
                    pct_change_7d = (
                        (latest_price - oldest_7d.modal_price) / oldest_7d.modal_price * 100
                    )

            # Determine trend
            if pct_change_7d > 2:
                trend = "up"
            elif pct_change_7d < -2:
                trend = "down"
            else:
                trend = "stable"

            # Check for price drop alert
            alert = None
            if pct_change_7d < -5:
                alert = {
                    "type": "price_drop",
                    "message": f"{crop.title()} prices down {abs(pct_change_7d):.1f}% in 7 days",
                }

            price_data = PriceData(
                crop=crop,
                latest_price=latest_price,
                min_price_30d=min_30d,
                max_price_30d=max_30d,
                avg_price_30d=avg_30d,
                msp=latest.msp,
                price_trend=trend,
                pct_change_7d=round(pct_change_7d, 2),
                alert=alert,
            )
            prices_data.append(price_data)

        return prices_data

    async def get_weather_forecast(self, district: str) -> WeatherData:
        """Get 5-day weather forecast for farmer's district."""
        today = datetime.utcnow().date()
        five_days_later = today + timedelta(days=5)

        stmt = (
            select(WeatherObservation)
            .where(
                and_(
                    WeatherObservation.district == district,
                    WeatherObservation.date >= today,
                    WeatherObservation.date <= five_days_later,
                )
            )
            .order_by(WeatherObservation.date, WeatherObservation.time)
        )
        result = await self.db.execute(stmt)
        observations = result.scalars().all()

        # Group by date and aggregate
        forecast_5d = []
        processed_dates = set()
        current_temp = None

        for obs in observations:
            # Get current temp from latest observation
            if current_temp is None and obs.date == today:
                current_temp = obs.temperature_c

            if obs.date not in processed_dates:
                processed_dates.add(obs.date)

                # Get all observations for this date
                day_obs = [o for o in observations if o.date == obs.date]

                temps = [o.temperature_c for o in day_obs if o.temperature_c]
                precips = [o.precipitation_mm for o in day_obs if o.precipitation_mm]
                humidities = [o.humidity_pct for o in day_obs if o.humidity_pct]

                high_temp = max(temps) if temps else None
                low_temp = min(temps) if temps else None
                total_precip = sum(precips) if precips else 0
                avg_humidity = sum(humidities) / len(humidities) if humidities else 50

                # Determine condition based on precipitation
                if total_precip > 5:
                    condition = "Rainy"
                elif total_precip > 1:
                    condition = "Cloudy"
                else:
                    condition = "Sunny"

                day_name = obs.date.strftime("%a")

                forecast_5d.append(
                    WeatherForecastDay(
                        date=obs.date.isoformat(),
                        day=day_name,
                        high=high_temp or 0,
                        low=low_temp or 0,
                        condition=condition,
                        precipitation_mm=round(total_precip, 1),
                        humidity_pct=round(avg_humidity),
                    )
                )

        return WeatherData(
            district=district,
            current_temp=current_temp,
            forecast_5d=forecast_5d[:5],  # Limit to 5 days
        )

    async def get_eligible_schemes(
        self,
        crops: List[str],
        district: str,
        land_hectares: Optional[float],
    ) -> List[SchemeData]:
        """Get government schemes matching farmer's profile."""
        schemes_data = []

        stmt = select(GovernmentScheme).where(GovernmentScheme.active == True)
        result = await self.db.execute(stmt)
        all_schemes = result.scalars().all()

        for scheme in all_schemes:
            # Check farm size eligibility
            size_match = True
            if land_hectares is not None:
                if scheme.min_hectares and land_hectares < scheme.min_hectares:
                    size_match = False
                if scheme.max_hectares and land_hectares > scheme.max_hectares:
                    size_match = False

            # Check crop eligibility
            crop_match = True
            if scheme.eligible_crops and crops:
                eligible_crop_list = json.loads(scheme.eligible_crops) if isinstance(
                    scheme.eligible_crops, str
                ) else scheme.eligible_crops
                crop_match = any(c in eligible_crop_list for c in crops)

            # Check district eligibility
            district_match = (
                scheme.state == "All India"
                or (scheme.state and district and district.lower() in scheme.state.lower())
            )

            eligible = size_match and crop_match and district_match

            scheme_data = SchemeData(
                id=scheme.id,
                name=scheme.name,
                eligible=eligible,
                description=scheme.description or "",
                min_hectares=scheme.min_hectares,
                max_hectares=scheme.max_hectares,
                amount_per_acre=scheme.amount_per_acre,
                details_url=scheme.details_url,
            )
            schemes_data.append(scheme_data)

        # Sort by eligibility (eligible first)
        schemes_data.sort(key=lambda x: (not x.eligible, x.name))

        return schemes_data[:10]  # Limit to top 10 schemes

    async def get_farmer_stats(self, farmer_id: int) -> FarmerStats:
        """Get farmer interaction statistics."""
        # Count conversations
        stmt = (
            select(func.count(Conversation.id))
            .where(
                and_(
                    Conversation.farmer_id == farmer_id,
                    Conversation.direction == "inbound",
                )
            )
        )
        result = await self.db.execute(stmt)
        queries_asked = result.scalar() or 0

        stmt = (
            select(func.count(Conversation.id))
            .where(
                and_(
                    Conversation.farmer_id == farmer_id,
                    Conversation.direction == "outbound",
                )
            )
        )
        result = await self.db.execute(stmt)
        responses = result.scalar() or 0

        # Get last query timestamp
        stmt = (
            select(Conversation.created_at)
            .where(Conversation.farmer_id == farmer_id)
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        last_query_at = result.scalar()

        return FarmerStats(
            queries_asked=queries_asked,
            queries_answered=responses,
            messages_received=queries_asked,
            messages_sent=responses,
            last_query_at=last_query_at,
        )

    async def get_recent_advisories(
        self, farmer_id: int, days: int = 7
    ) -> List[AdvisoryCard]:
        """Return non-dismissed advisories from the last N days for the dashboard."""
        from datetime import timedelta
        cutoff = datetime.utcnow().date() - timedelta(days=days)

        stmt = (
            select(Advisory, AdvisoryRule)
            .join(AdvisoryRule, Advisory.rule_id == AdvisoryRule.id)
            .where(
                and_(
                    Advisory.farmer_id == farmer_id,
                    Advisory.advisory_date >= cutoff,
                    Advisory.dismissed_at.is_(None),
                )
            )
            .order_by(Advisory.advisory_date.desc(), Advisory.risk_level.desc())
        )
        result = await self.db.execute(stmt)
        cards: List[AdvisoryCard] = []
        for adv, rule in result.all():
            cards.append(
                AdvisoryCard(
                    id=adv.id,
                    advisory_type=rule.advisory_type if rule else None,
                    crop=adv.crop,
                    advisory_date=adv.advisory_date,
                    valid_until=adv.valid_until,
                    risk_level=adv.risk_level,
                    title=adv.title,
                    message=adv.message,
                    action_hint=adv.action_hint,
                    source_citation=adv.source_citation,
                )
            )
        return cards

    async def get_farmer_dashboard_data(self, farmer_id: int) -> FarmerDashboardData:
        """Get complete farmer dashboard data."""
        farmer = await self.get_farmer(farmer_id)
        if not farmer:
            raise ValueError(f"Farmer {farmer_id} not found")

        # Get crops
        crops = await self.get_farmer_crops(farmer_id)

        # Get prices
        prices = await self.get_crop_prices_30d(
            crops=crops,
            district=farmer.district or "Maharashtra",
        )

        # Get weather
        weather = await self.get_weather_forecast(
            district=farmer.district or "Maharashtra"
        )

        # Get schemes
        schemes = await self.get_eligible_schemes(
            crops=crops,
            district=farmer.district or "Maharashtra",
            land_hectares=float(farmer.land_hectares) if farmer.land_hectares else None,
        )

        # Get stats
        stats = await self.get_farmer_stats(farmer_id)

        # Get advisories (Phase 4 Step 3)
        advisories = await self.get_recent_advisories(farmer_id)

        # Build response
        return FarmerDashboardData(
            farmer=FarmerInfo(
                name=farmer.name,
                district=farmer.district,
                land_hectares=float(farmer.land_hectares) if farmer.land_hectares else None,
                plan_tier=farmer.plan_tier,
                preferred_language=farmer.preferred_language,
            ),
            crops=[{"crop": c, "count_following": 1} for c in crops],
            prices=prices,
            weather=weather,
            schemes=schemes,
            advisories=advisories,
            stats=stats,
            generated_at=datetime.utcnow(),
        )
