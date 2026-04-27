"""Query layer for weather data (Phase 2 Module 1)."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.weather import WeatherObservation
from src.weather.models import WeatherQuery, WeatherQueryResult, WeatherRecord

logger = logging.getLogger(__name__)


class WeatherRepository:
    """Query weather observations from database (or cache)."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with a database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def query(
        self,
        q: WeatherQuery,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> WeatherQueryResult:
        """Fetch today's weather observation for a metric + APMC.

        Returns today's observation + next 3 days forecast if available.

        Args:
            q: WeatherQuery with metric and optional APMC

        Returns:
            WeatherQueryResult with found=True if data exists, False otherwise
        """
        if not q.apmc:
            if lat is not None and lon is not None:
                return await self._query_live(q, lat, lon)
            logger.warning("query: no APMC provided")
            return WeatherQueryResult(
                found=False,
                query=q,
                error="APMC not registered. Please complete onboarding.",
            )

        try:
            # Query today's observation
            today = date.today()
            stmt = select(WeatherObservation).where(
                WeatherObservation.date == today,
                WeatherObservation.apmc == q.apmc,
                WeatherObservation.metric == q.metric,
                WeatherObservation.forecast_days_ahead == 0,
            ).order_by(WeatherObservation.fetched_at.desc()).limit(1)

            result = await self.session.execute(stmt)
            obs = result.scalar()

            if not obs:
                logger.warning(
                    "query: no weather data found for date=%s apmc=%s metric=%s",
                    today, q.apmc, q.metric,
                )
                if lat is not None and lon is not None:
                    return await self._query_live(q, lat, lon)
                return WeatherQueryResult(found=False, query=q)

            # Check if stale (>6 hours old)
            is_stale = obs.fetched_at < datetime.now(obs.fetched_at.tzinfo) - timedelta(hours=6)

            # Convert ORM object to dataclass
            record = WeatherRecord(
                date=obs.date,
                apmc=obs.apmc,
                metric=obs.metric,
                value=obs.value,
                unit=obs.unit,
                min_value=obs.min_value,
                max_value=obs.max_value,
                condition=obs.condition,
                source=obs.source,
            )

            # Fetch 3-day forecast if requested
            forecast = []
            if q.days_ahead > 0:
                forecast_stmt = select(WeatherObservation).where(
                    WeatherObservation.apmc == q.apmc,
                    WeatherObservation.metric == q.metric,
                    WeatherObservation.forecast_days_ahead.in_([1, 2, 3]),
                    WeatherObservation.date.between(today, today + timedelta(days=3)),
                ).order_by(WeatherObservation.forecast_days_ahead)

                forecast_result = await self.session.execute(forecast_stmt)
                forecast_records = forecast_result.scalars().all()

                forecast = [
                    WeatherRecord(
                        date=f_obs.date,
                        apmc=f_obs.apmc,
                        metric=f_obs.metric,
                        value=f_obs.value,
                        unit=f_obs.unit,
                        min_value=f_obs.min_value,
                        max_value=f_obs.max_value,
                        condition=f_obs.condition,
                        source=f_obs.source,
                    )
                    for f_obs in forecast_records
                ]

            logger.info(
                "query: found weather for apmc=%s metric=%s (stale=%s)",
                q.apmc,
                q.metric,
                is_stale,
            )

            return WeatherQueryResult(
                found=True,
                query=q,
                record=record,
                forecast=forecast if forecast else None,
                stale=is_stale,
                source=obs.source,
            )

        except Exception as exc:
            logger.exception("query: failed to fetch weather for %s", q.apmc)
            return WeatherQueryResult(
                found=False,
                query=q,
                error=f"Database query failed: {type(exc).__name__}",
            )

    async def _query_live(
        self, q: WeatherQuery, lat: float, lon: float
    ) -> WeatherQueryResult:
        """Fallback: call OpenWeather API with village coordinates."""
        from src.config import settings
        api_key = settings.openweather_api_key
        if not api_key:
            logger.warning("_query_live: no openweather_api_key configured")
            return WeatherQueryResult(found=False, query=q)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
                )
                resp.raise_for_status()
                data = resp.json()

            main = data.get("main", {})
            wind = data.get("wind", {})
            rain = data.get("rain", {})
            weather_list = data.get("weather", [])
            condition = weather_list[0].get("description") if weather_list else None

            metric_map = {
                "temperature": ("temp", "°C"),
                "humidity": ("humidity", "%"),
                "pressure": ("pressure", "hPa"),
                "wind_speed": None,
                "rainfall": None,
            }

            value: Optional[Decimal] = None
            unit = ""
            min_val = max_val = None

            if q.metric == "temperature" and "temp" in main:
                value = Decimal(str(main["temp"])).quantize(Decimal("0.1"))
                unit = "°C"
                if "temp_min" in main:
                    min_val = Decimal(str(main["temp_min"])).quantize(Decimal("0.1"))
                if "temp_max" in main:
                    max_val = Decimal(str(main["temp_max"])).quantize(Decimal("0.1"))
            elif q.metric == "humidity" and "humidity" in main:
                value = Decimal(str(main["humidity"]))
                unit = "%"
            elif q.metric == "pressure" and "pressure" in main:
                value = Decimal(str(main["pressure"]))
                unit = "hPa"
            elif q.metric == "wind_speed" and "speed" in wind:
                value = (Decimal(str(wind["speed"])) * Decimal("3.6")).quantize(Decimal("0.1"))
                unit = "km/h"
            elif q.metric == "rainfall":
                rain_val = rain.get("1h", 0)
                value = Decimal(str(rain_val))
                unit = "mm"

            if value is None:
                return WeatherQueryResult(found=False, query=q)

            record = WeatherRecord(
                date=date.today(),
                apmc=q.apmc or f"{lat},{lon}",
                metric=q.metric,
                value=value,
                unit=unit,
                min_value=min_val,
                max_value=max_val,
                condition=condition,
                source="openweather_live",
            )
            logger.info("_query_live: got %s=%.1f%s from OpenWeather", q.metric, float(value), unit)
            return WeatherQueryResult(found=True, query=q, record=record, source="openweather_live")

        except Exception as exc:
            logger.exception("_query_live: failed for lat=%s lon=%s: %s", lat, lon, exc)
            return WeatherQueryResult(found=False, query=q, error=str(exc))

    async def get_advisory(self, apmc: str, metric: str) -> Optional[str]:
        """Fetch crop-specific advisory for a metric at an APMC.

        Args:
            apmc: APMC code
            metric: Weather metric (temperature, rainfall, etc.)

        Returns:
            Advisory text or None if not available
        """
        try:
            today = date.today()
            stmt = select(WeatherObservation.advisory).where(
                WeatherObservation.date == today,
                WeatherObservation.apmc == apmc,
                WeatherObservation.metric == metric,
                WeatherObservation.advisory != None,
            ).order_by(WeatherObservation.fetched_at.desc()).limit(1)

            result = await self.session.execute(stmt)
            advisory = result.scalar()
            return advisory

        except Exception as exc:
            logger.exception("get_advisory: failed for apmc=%s metric=%s", apmc, metric)
            return None
