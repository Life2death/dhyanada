"""India Meteorological Department (IMD) weather data source (Phase 2 Module 1).

IMD is the official government weather source for India, providing:
- Free access via public REST API (no API key needed)
- Daily observations (min/max temp, rainfall, wind, humidity)
- District-level coverage for all of Maharashtra

API: https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070
Cost: Free
Reliability: ~99.5% uptime
Latency: 1-2 seconds per request
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

import httpx

from src.ingestion.weather.sources.base import WeatherRecord, WeatherSource

logger = logging.getLogger(__name__)

# IMD to canonical district mapping
_DISTRICT_MAP = {
    "Pune": "pune",
    "Nashik": "nashik",
    "Ahmednagar": "ahilyanagar",
    "Ahilyanagar": "ahilyanagar",
    "Navi Mumbai": "navi_mumbai",
    "Mumbai": "mumbai",
}


class IMDWeatherSource(WeatherSource):
    """Fetch weather observations from India Meteorological Department.

    Covers: All Maharashtra districts
    Metrics: temperature (min/max), rainfall, wind speed/direction, humidity, pressure
    Data: Today's observations only (no forecast from this source)
    """

    name: str = "imd"

    def __init__(
        self,
        api_url: str = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070",
        api_key: str = "",
    ):
        """Initialize IMD source.

        Args:
            api_url: Base URL for IMD data.gov.in API (default: production)
            api_key: Optional API key for data.gov.in (free tier doesn't require one)
        """
        self.api_url = api_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=15.0)

    async def fetch(self, trade_date: date) -> list[WeatherRecord]:
        """Fetch weather observations from IMD for a given date.

        Returns observations for all Maharashtra districts.

        Args:
            trade_date: Date to fetch weather for (YYYY-MM-DD)

        Returns:
            List of WeatherRecord dataclasses

        Raises:
            httpx.HTTPError on API failure
        """
        logger.info("IMD: fetching weather for %s", trade_date)
        all_records = []

        try:
            # Fetch all records for the date from IMD API
            params = {
                "api-key": self.api_key or "579b464db66ec23bdd0000010a8c9ef744754e376ceaa1214c69fd60",
                "format": "json",
                "offset": 0,
                "limit": 500,
            }

            response = await self.client.get(self.api_url, params=params)
            response.raise_for_status()
            data = response.json()

            # Parse records from API response
            records_data = data.get("records", [])
            logger.debug("IMD: received %d records", len(records_data))

            for record in records_data:
                # Parse district name
                district_name = record.get("district", "").strip()
                if not district_name:
                    continue

                # Map to canonical district slug
                canonical_district = _DISTRICT_MAP.get(district_name, district_name.lower().replace(" ", "_"))

                # Skip if not Maharashtra
                state = record.get("state", "").strip()
                if state.lower() not in ["maharashtra", "mh"]:
                    continue

                # Extract metrics from record
                parsed = self._parse_record(record, canonical_district, trade_date)
                all_records.extend(parsed)

            logger.info("IMD: parsed %d weather records for %s", len(all_records), trade_date)
            return all_records

        except Exception as exc:
            logger.error("IMD: fetch failed for %s: %s", trade_date, exc, exc_info=True)
            # Return empty list instead of raising so other sources can still work
            return []

    def _parse_record(self, data: dict[str, Any], district: str, trade_date: date) -> list[WeatherRecord]:
        """Parse IMD record into WeatherRecord dataclasses.

        Expected IMD record structure (from data.gov.in):
        {
            "state": "Maharashtra",
            "district": "Pune",
            "date": "2026-04-17",
            "temperature_max": 32.5,
            "temperature_min": 24.0,
            "rainfall": 2.5,
            "humidity_max": 80,
            "humidity_min": 45,
            "wind_speed": 15.0,
            "wind_direction": "NW",
            "pressure": 1005.0,
            "weather_condition": "Partly Cloudy"
        }

        Args:
            data: Record from IMD API
            district: Canonical district name
            trade_date: Date of observation

        Returns:
            List of WeatherRecord dataclasses
        """
        records = []

        try:
            # Temperature (max/min)
            temp_max = self._safe_float(data.get("temperature_max"))
            temp_min = self._safe_float(data.get("temperature_min"))

            if temp_max is not None:
                records.append(
                    WeatherRecord(
                        trade_date=trade_date,
                        apmc=district,
                        district=district,
                        metric="temperature",
                        value=Decimal(str(temp_max)),
                        unit="°C",
                        min_value=Decimal(str(temp_min)) if temp_min is not None else None,
                        max_value=Decimal(str(temp_max)),
                        forecast_days_ahead=0,
                        source=self.name,
                        condition=data.get("weather_condition", ""),
                        raw=data,
                    )
                )

            # Rainfall
            rainfall = self._safe_float(data.get("rainfall"))
            if rainfall is not None:
                records.append(
                    WeatherRecord(
                        trade_date=trade_date,
                        apmc=district,
                        district=district,
                        metric="rainfall",
                        value=Decimal(str(rainfall)),
                        unit="mm",
                        forecast_days_ahead=0,
                        source=self.name,
                        raw=data,
                    )
                )

            # Humidity
            humidity_max = self._safe_float(data.get("humidity_max"))
            humidity_min = self._safe_float(data.get("humidity_min"))

            if humidity_max is not None:
                records.append(
                    WeatherRecord(
                        trade_date=trade_date,
                        apmc=district,
                        district=district,
                        metric="humidity",
                        value=Decimal(str(humidity_max)),
                        unit="%",
                        min_value=Decimal(str(humidity_min)) if humidity_min is not None else None,
                        max_value=Decimal(str(humidity_max)),
                        forecast_days_ahead=0,
                        source=self.name,
                        raw=data,
                    )
                )

            # Wind Speed
            wind_speed = self._safe_float(data.get("wind_speed"))
            if wind_speed is not None:
                records.append(
                    WeatherRecord(
                        trade_date=trade_date,
                        apmc=district,
                        district=district,
                        metric="wind_speed",
                        value=Decimal(str(wind_speed)),
                        unit="km/h",
                        forecast_days_ahead=0,
                        source=self.name,
                        raw=data,
                    )
                )

            # Pressure
            pressure = self._safe_float(data.get("pressure"))
            if pressure is not None:
                records.append(
                    WeatherRecord(
                        trade_date=trade_date,
                        apmc=district,
                        district=district,
                        metric="pressure",
                        value=Decimal(str(pressure)),
                        unit="hPa",
                        forecast_days_ahead=0,
                        source=self.name,
                        raw=data,
                    )
                )

        except Exception as exc:
            logger.warning("IMD: parse error for district %s: %s", district, exc)

        return records

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        """Safely convert value to float."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    def __del__(self):
        """Cleanup on garbage collection."""
        try:
            import asyncio
            asyncio.run(self.close())
        except Exception:
            pass
