"""Integration test for the advisory pipeline — DB → engine → dashboard → dismiss.

Uses in-memory SQLite so we exercise the real SQLAlchemy ORM queries and
rule-match logic end-to-end without touching WhatsApp / external APIs.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.advisory.engine import generate_for_farmer
from src.advisory.models import RuleData
from src.advisory.repository import AdvisoryRepository
from src.farmer.repository import FarmerRepository
from src.models.advisory import Advisory
from src.models.advisory_rule import AdvisoryRule
from src.models.base import Base
from src.models.farmer import CropOfInterest, Farmer
from src.models.weather import WeatherObservation


# Only the tables we need — avoids SQLite vs. UUID/gen_random_uuid incompatibilities
# with schemes/msp_alerts, which aren't used in the advisory flow.
_NEEDED_TABLES = [
    "farmers",
    "crops_of_interest",
    "weather_observations",
    "advisory_rules",
    "advisories",
]


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        tables = [t for t in Base.metadata.sorted_tables if t.name in _NEEDED_TABLES]
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    async with factory() as session:
        yield session

    await engine.dispose()


async def _seed_farmer(db: AsyncSession) -> Farmer:
    f = Farmer(
        phone="+919876543210",
        name="Test Farmer",
        district="pune",
        land_hectares=Decimal("3.5"),
        preferred_language="mr",
        plan_tier="free",
        subscription_status="active",
        onboarding_state="active",
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)
    db.add(CropOfInterest(farmer_id=f.id, crop="tomato"))
    db.add(CropOfInterest(farmer_id=f.id, crop="onion"))
    await db.commit()
    return f


async def _seed_late_blight_forecast(db: AsyncSession, farmer_district: str) -> None:
    """3 consecutive days of 92% RH + 22°C in the farmer's district."""
    today = date.today()
    for i in range(3):
        d = today + timedelta(days=i)
        db.add(
            WeatherObservation(
                date=d, apmc="niphad", district=farmer_district, taluka="niphad",
                metric="temperature", value=Decimal("22"), unit="C",
                min_value=Decimal("18"), max_value=Decimal("22"),
                forecast_days_ahead=i, source="imd",
            )
        )
        db.add(
            WeatherObservation(
                date=d, apmc="niphad", district=farmer_district, taluka="niphad",
                metric="humidity", value=Decimal("92"), unit="%",
                forecast_days_ahead=i, source="imd",
            )
        )
    await db.commit()


async def _seed_late_blight_rule(db: AsyncSession) -> AdvisoryRule:
    repo = AdvisoryRepository(db)
    return await repo.upsert_rule(
        RuleData(
            rule_key="late_blight_tomato",
            advisory_type="disease",
            crop="tomato",
            min_humidity_pct=90,
            min_temp_c=10,
            max_temp_c=24,
            consecutive_days=2,
            risk_level="high",
            title_en="Late blight risk on tomato",
            message_en="Humidity >90% with cool temps forecast — late blight risk.",
            action_hint="Apply preventive mancozeb spray.",
            source_citation="ICAR-IIHR",
        )
    )


@pytest.mark.asyncio
async def test_engine_generates_advisory_for_matching_weather(db):
    farmer = await _seed_farmer(db)
    await _seed_late_blight_forecast(db, farmer.district)
    rule = await _seed_late_blight_rule(db)

    created = await generate_for_farmer(db, farmer.id)

    assert len(created) == 1
    assert created[0].rule_id == rule.id
    assert created[0].risk_level == "high"
    assert created[0].crop == "tomato"
    assert created[0].title == "Late blight risk on tomato"


@pytest.mark.asyncio
async def test_engine_is_idempotent_same_day(db):
    farmer = await _seed_farmer(db)
    await _seed_late_blight_forecast(db, farmer.district)
    await _seed_late_blight_rule(db)

    first = await generate_for_farmer(db, farmer.id)
    second = await generate_for_farmer(db, farmer.id)

    assert len(first) == 1
    assert len(second) == 0  # dedup — no duplicate rows on re-run


@pytest.mark.asyncio
async def test_engine_skips_when_weather_neutral(db):
    farmer = await _seed_farmer(db)
    # Neutral: 28°C, 60% RH, no rain — shouldn't trigger disease rule
    today = date.today()
    for i in range(3):
        d = today + timedelta(days=i)
        db.add(WeatherObservation(
            date=d, apmc="x", district=farmer.district, taluka="x",
            metric="temperature", value=Decimal("28"), unit="C",
            min_value=Decimal("22"), max_value=Decimal("28"),
            forecast_days_ahead=i, source="imd",
        ))
        db.add(WeatherObservation(
            date=d, apmc="x", district=farmer.district, taluka="x",
            metric="humidity", value=Decimal("60"), unit="%",
            forecast_days_ahead=i, source="imd",
        ))
    await db.commit()
    await _seed_late_blight_rule(db)

    created = await generate_for_farmer(db, farmer.id)
    assert created == []


@pytest.mark.asyncio
async def test_engine_skips_when_rule_inactive(db):
    farmer = await _seed_farmer(db)
    await _seed_late_blight_forecast(db, farmer.district)
    rule = await _seed_late_blight_rule(db)

    repo = AdvisoryRepository(db)
    await repo.soft_delete_rule(rule.id)

    created = await generate_for_farmer(db, farmer.id)
    assert created == []


@pytest.mark.asyncio
async def test_engine_skips_wrong_district(db):
    farmer = await _seed_farmer(db)
    await _seed_late_blight_forecast(db, farmer.district)
    # Rule restricted to a different district
    repo = AdvisoryRepository(db)
    await repo.upsert_rule(
        RuleData(
            rule_key="disease_nashik_only",
            advisory_type="disease",
            crop="tomato",
            eligible_districts=["nashik"],
            min_humidity_pct=90,
            consecutive_days=2,
            risk_level="high",
            title_en="Nashik-only",
            message_en="x",
            action_hint="x",
        )
    )

    created = await generate_for_farmer(db, farmer.id)
    assert created == []


@pytest.mark.asyncio
async def test_engine_skips_when_farmer_has_no_forecast(db):
    farmer = await _seed_farmer(db)
    await _seed_late_blight_rule(db)
    # No weather observations inserted

    created = await generate_for_farmer(db, farmer.id)
    assert created == []


@pytest.mark.asyncio
async def test_dashboard_repository_surfaces_advisory(db):
    farmer = await _seed_farmer(db)
    await _seed_late_blight_forecast(db, farmer.district)
    await _seed_late_blight_rule(db)
    await generate_for_farmer(db, farmer.id)

    farmer_repo = FarmerRepository(db)
    cards = await farmer_repo.get_recent_advisories(farmer.id)

    assert len(cards) == 1
    card = cards[0]
    assert card.risk_level == "high"
    assert card.advisory_type == "disease"
    assert card.crop == "tomato"
    assert "mancozeb" in card.action_hint


@pytest.mark.asyncio
async def test_dismiss_hides_advisory_from_dashboard(db):
    farmer = await _seed_farmer(db)
    await _seed_late_blight_forecast(db, farmer.district)
    await _seed_late_blight_rule(db)
    created = await generate_for_farmer(db, farmer.id)
    adv_id = created[0].id

    adv_repo = AdvisoryRepository(db)
    ok = await adv_repo.dismiss(adv_id, farmer.id)
    assert ok is True

    farmer_repo = FarmerRepository(db)
    cards = await farmer_repo.get_recent_advisories(farmer.id)
    assert cards == []

    # Dismissing a wrong farmer_id should not crash and should return False
    ok2 = await adv_repo.dismiss(adv_id, farmer_id=9999)
    assert ok2 is False


@pytest.mark.asyncio
async def test_mark_whatsapp_delivered(db):
    farmer = await _seed_farmer(db)
    await _seed_late_blight_forecast(db, farmer.district)
    await _seed_late_blight_rule(db)
    created = await generate_for_farmer(db, farmer.id)

    adv_repo = AdvisoryRepository(db)
    await adv_repo.mark_whatsapp_delivered(created[0].id, "msg_abc123")

    reloaded = await adv_repo.list_recent_across_farmers()
    assert reloaded[0].delivered_via["whatsapp"] == "msg_abc123"
    assert reloaded[0].delivered_via["dashboard"] is True  # original flag preserved
