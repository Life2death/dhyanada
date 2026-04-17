"""Tests for Phase 2 Module 1 — Weather Integration."""
from __future__ import annotations

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.classifier.classify import classify_regex
from src.classifier.intents import Intent, IntentResult
from src.ingestion.weather.sources.base import WeatherRecord
from src.ingestion.weather.normalizer import normalize_metric, normalize_apmc
from src.ingestion.weather.merger import pick_winners
from src.weather.formatter import format_weather_reply
from src.weather.models import WeatherQuery, WeatherQueryResult, WeatherRecord as QueryWeatherRecord


class TestWeatherIntentClassification:
    """Test weather query intent classification (regex + LLM)."""

    def test_english_weather_pattern(self):
        """Test English weather query detection."""
        result = classify_regex("What's the weather today?")
        assert result.intent == Intent.WEATHER_QUERY
        assert result.confidence == 1.0
        assert result.source == "regex"

    def test_marathi_weather_pattern(self):
        """Test Marathi weather query detection (हवामान)."""
        result = classify_regex("आजचे हवामान काय आहे?")
        assert result.intent == Intent.WEATHER_QUERY
        assert result.confidence == 1.0

    def test_marathi_rainfall_pattern(self):
        """Test Marathi rainfall query (पाऊस)."""
        result = classify_regex("पाऊस होणार का?")
        assert result.intent == Intent.WEATHER_QUERY
        assert result.confidence == 1.0

    def test_temperature_extraction(self):
        """Test temperature metric extraction."""
        result = classify_regex("What's the temperature in Pune?")
        assert result.intent == Intent.WEATHER_QUERY
        assert result.commodity == "temperature"
        assert result.district == "pune"

    def test_rainfall_extraction_marathi(self):
        """Test rainfall metric extraction in Marathi."""
        result = classify_regex("नाशिक मध्ये पाऊस कितना?")
        assert result.intent == Intent.WEATHER_QUERY
        assert result.commodity == "rainfall"
        assert result.district == "nashik"

    def test_humidity_extraction(self):
        """Test humidity metric extraction."""
        result = classify_regex("Pune humidity today")
        assert result.intent == Intent.WEATHER_QUERY
        assert result.commodity == "humidity"
        assert result.district == "pune"

    def test_wind_extraction(self):
        """Test wind metric extraction."""
        result = classify_regex("Wind speed Mumbai")
        assert result.intent == Intent.WEATHER_QUERY
        assert result.commodity == "wind_speed"
        assert result.district == "mumbai"

    def test_metric_not_extracted(self):
        """Test when weather query but metric not extracted."""
        result = classify_regex("How's the weather?")
        assert result.intent == Intent.WEATHER_QUERY
        assert result.commodity is None  # Generic weather, no specific metric


class TestWeatherNormalization:
    """Test metric and APMC normalization."""

    def test_normalize_temperature_variants(self):
        """Test various temperature field names normalize to 'temperature'."""
        assert normalize_metric("temperature") == "temperature"
        assert normalize_metric("temp") == "temperature"
        assert normalize_metric("तापमान") == "temperature"
        assert normalize_metric("temperature_max") == "temperature"

    def test_normalize_rainfall_variants(self):
        """Test rainfall name variants."""
        assert normalize_metric("rainfall") == "rainfall"
        assert normalize_metric("rain") == "rainfall"
        assert normalize_metric("precipitation") == "rainfall"
        assert normalize_metric("पाऊस") == "rainfall"

    def test_normalize_apmc_pune(self):
        """Test APMC normalization for Pune."""
        assert normalize_apmc("pune") == "pune"
        assert normalize_apmc("Pune") == "pune"
        assert normalize_apmc("पुणे") == "pune"

    def test_normalize_apmc_nashik(self):
        """Test APMC normalization for Nashik."""
        assert normalize_apmc("nashik") == "nashik"
        assert normalize_apmc("Nashik") == "nashik"
        assert normalize_apmc("नाशिक") == "nashik"

    def test_unknown_metric_returns_none(self):
        """Test unknown metric returns None."""
        assert normalize_metric("unknown_metric") is None
        assert normalize_metric("") is None

    def test_unknown_apmc_returns_none(self):
        """Test unknown APMC returns None."""
        assert normalize_apmc("unknown_apmc") is None


class TestWeatherMerger:
    """Test deduplication and source preference."""

    def test_pick_winners_single_source(self):
        """Test that single source records pass through unchanged."""
        records = [
            WeatherRecord(
                trade_date=date.today(),
                apmc="pune",
                district="pune",
                metric="temperature",
                value=Decimal("28.5"),
                unit="°C",
                forecast_days_ahead=0,
                source="imd",
            ),
        ]
        winners = pick_winners(records)
        assert len(winners) == 1
        assert winners[0].source == "imd"

    def test_pick_winners_prefers_imd(self):
        """Test that IMD source is preferred over OpenWeather."""
        records = [
            WeatherRecord(
                trade_date=date.today(),
                apmc="pune",
                district="pune",
                metric="temperature",
                value=Decimal("28.0"),
                unit="°C",
                forecast_days_ahead=0,
                source="openweather",
            ),
            WeatherRecord(
                trade_date=date.today(),
                apmc="pune",
                district="pune",
                metric="temperature",
                value=Decimal("28.5"),
                unit="°C",
                forecast_days_ahead=0,
                source="imd",
            ),
        ]
        winners = pick_winners(records)
        assert len(winners) == 2  # Both kept
        # IMD should appear first (higher priority)
        assert winners[0].source == "imd"


class TestWeatherFormatter:
    """Test Marathi and English formatting."""

    def test_format_weather_reply_marathi(self):
        """Test Marathi weather reply formatting."""
        from src.weather.models import WeatherRecord as WR

        record = WR(
            date=date.today(),
            apmc="pune",
            metric="temperature",
            value=Decimal("28.5"),
            unit="°C",
            min_value=Decimal("24.0"),
            max_value=Decimal("32.0"),
            source="imd",
        )
        result = WeatherQueryResult(
            found=True,
            query=WeatherQuery(metric="temperature", apmc="pune"),
            record=record,
            stale=False,
            source="imd",
        )

        reply = format_weather_reply(result, lang="mr")

        assert "तापमान" in reply or "Temperature" in reply  # Should have Marathi or English
        assert "28.5" in reply or "28" in reply  # Should have temperature value
        assert "पुणे" in reply or "Pune" in reply  # Should have APMC

    def test_format_weather_reply_english(self):
        """Test English weather reply formatting."""
        from src.weather.models import WeatherRecord as WR

        record = WR(
            date=date.today(),
            apmc="nashik",
            metric="rainfall",
            value=Decimal("15.0"),
            unit="mm",
            source="openweather",
        )
        result = WeatherQueryResult(
            found=True,
            query=WeatherQuery(metric="rainfall", apmc="nashik"),
            record=record,
            stale=False,
            source="openweather",
        )

        reply = format_weather_reply(result, lang="en")

        assert "Rainfall" in reply or "rainfall" in reply
        assert "15" in reply
        assert "Nashik" in reply or "nashik" in reply

    def test_format_weather_not_found(self):
        """Test formatting when weather data not found."""
        result = WeatherQueryResult(
            found=False,
            query=WeatherQuery(metric="temperature", apmc="pune"),
        )

        reply = format_weather_reply(result, lang="mr")
        assert "उपलब्ध नाही" in reply or "not available" in reply

    def test_format_weather_stale_data(self):
        """Test formatting includes staleness warning."""
        from src.weather.models import WeatherRecord as WR

        record = WR(
            date=date.today(),
            apmc="pune",
            metric="humidity",
            value=Decimal("65.0"),
            unit="%",
            source="imd",
        )
        result = WeatherQueryResult(
            found=True,
            query=WeatherQuery(metric="humidity", apmc="pune"),
            record=record,
            stale=True,  # Mark as stale
            source="imd",
        )

        reply = format_weather_reply(result, lang="mr")
        assert "⚠️" in reply  # Should have warning emoji


class TestWeatherHandler:
    """Test weather intent handler."""

    @pytest.mark.asyncio
    async def test_weather_handler_routes_query(self):
        """Test WeatherHandler routes weather query to formatter."""
        from src.weather.handler import WeatherHandler

        mock_session = MagicMock()
        handler = WeatherHandler(mock_session)

        # Mock repository query
        handler.repo.query = AsyncMock(
            return_value=WeatherQueryResult(
                found=True,
                query=WeatherQuery(metric="temperature", apmc="pune"),
                record=QueryWeatherRecord(
                    date=date.today(),
                    apmc="pune",
                    metric="temperature",
                    value=Decimal("28.5"),
                    unit="°C",
                ),
            )
        )

        intent = IntentResult(
            intent=Intent.WEATHER_QUERY,
            confidence=1.0,
            commodity="temperature",
            district="pune",
        )

        reply = await handler.handle(intent, farmer_apmc="pune", farmer_language="mr")

        assert reply  # Should have a reply
        assert "28" in reply or "तापमान" in reply  # Should mention temperature

    @pytest.mark.asyncio
    async def test_weather_handler_missing_metric(self):
        """Test handler when metric not extracted."""
        from src.weather.handler import WeatherHandler

        mock_session = MagicMock()
        handler = WeatherHandler(mock_session)

        intent = IntentResult(
            intent=Intent.WEATHER_QUERY,
            confidence=0.9,
            commodity=None,  # Metric not extracted
        )

        reply = await handler.handle(intent, farmer_apmc="pune", farmer_language="mr")

        # Should ask for clarification
        assert "कोण" in reply or "Which" in reply or "कुठले" in reply


class TestWeatherDataModel:
    """Test weather data models."""

    def test_weather_query_model(self):
        """Test WeatherQuery dataclass."""
        query = WeatherQuery(metric="rainfall", apmc="nashik", days_ahead=0)
        assert query.metric == "rainfall"
        assert query.apmc == "nashik"
        assert query.days_ahead == 0

    def test_weather_result_model(self):
        """Test WeatherQueryResult dataclass."""
        result = WeatherQueryResult(
            found=True,
            query=WeatherQuery(metric="temperature", apmc="pune"),
            stale=False,
        )
        assert result.found is True
        assert result.stale is False
        assert result.query.metric == "temperature"
