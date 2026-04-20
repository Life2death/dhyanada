"""OpenWeather API source — taluka-level weather fallback for Maharashtra.

Cost: Free tier (60 calls/min, 1M calls/month). At 350 talukas = 350 calls/run.
Endpoints: /weather (current, metric units — returns Celsius directly)
"""
from __future__ import annotations

import json
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx

from src.ingestion.weather.sources.base import WeatherRecord, WeatherSource

logger = logging.getLogger(__name__)

_DATA_FILE = Path(__file__).parent.parent / "data" / "maharashtra_talukas.json"


def _load_talukas() -> list[dict]:
    with _DATA_FILE.open() as f:
        return json.load(f)


class OpenWeatherSource(WeatherSource):
    """Fetch current weather from OpenWeather for every Maharashtra taluka (fallback).

    Uses metric units so temperature arrives in Celsius (no conversion needed).
    Falls back to this source when AgroMonitoring is unavailable.
    """

    name: str = "openweather"

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.openweathermap.org/data/2.5",
        talukas: list[dict] | None = None,
    ):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.client = httpx.AsyncClient(timeout=15.0)
        self.talukas = talukas if talukas is not None else _load_talukas()

    async def fetch(self, trade_date: date) -> list[WeatherRecord]:
        logger.info("OpenWeather: fetching weather for %d talukas on %s", len(self.talukas), trade_date)

        all_records: list[WeatherRecord] = []
        errors = 0

        for entry in self.talukas:
            taluka = entry["taluka"]
            district = entry["district"]

            try:
                response = await self.client.get(
                    f"{self.api_base}/weather",
                    params={
                        "lat": entry["lat"],
                        "lon": entry["lon"],
                        "appid": self.api_key,
                        "units": "metric",
                    },
                )
                response.raise_for_status()
                records = self._parse_response(response.json(), taluka, district, trade_date)
                all_records.extend(records)
            except Exception as exc:
                errors += 1
                logger.warning("OpenWeather: failed for taluka=%s: %s", taluka, exc)

        logger.info(
            "OpenWeather: fetched %d records across %d talukas (%d errors)",
            len(all_records), len(self.talukas), errors,
        )
        return all_records

    def _parse_response(
        self,
        data: dict,
        taluka: str,
        district: str,
        trade_date: date,
    ) -> list[WeatherRecord]:
        records: list[WeatherRecord] = []

        main = data.get("main", {})
        wind = data.get("wind", {})
        rain = data.get("rain", {})
        weather_list = data.get("weather", [])
        condition = weather_list[0].get("description") if weather_list else None

        def _rec(metric: str, value: Decimal, unit: str, **kwargs) -> WeatherRecord:
            return WeatherRecord(
                trade_date=trade_date,
                apmc=taluka,
                district=district,
                taluka=taluka,
                metric=metric,
                value=value,
                unit=unit,
                forecast_days_ahead=0,
                condition=condition,
                source=self.name,
                raw=data,
                **kwargs,
            )

        if "temp" in main:
            records.append(_rec(
                "temperature",
                Decimal(str(main["temp"])).quantize(Decimal("0.1")),
                "°C",
                min_value=Decimal(str(main["temp_min"])).quantize(Decimal("0.1")) if "temp_min" in main else None,
                max_value=Decimal(str(main["temp_max"])).quantize(Decimal("0.1")) if "temp_max" in main else None,
            ))

        if "humidity" in main:
            records.append(_rec("humidity", Decimal(str(main["humidity"])), "%"))

        if "pressure" in main:
            records.append(_rec("pressure", Decimal(str(main["pressure"])), "hPa"))

        if "speed" in wind:
            wind_kmh = (Decimal(str(wind["speed"])) * Decimal("3.6")).quantize(Decimal("0.1"))
            records.append(_rec("wind_speed", wind_kmh, "km/h"))

        if "1h" in rain:
            records.append(_rec("rainfall", Decimal(str(rain["1h"])), "mm"))

        return records

    async def close(self) -> None:
        await self.client.aclose()
