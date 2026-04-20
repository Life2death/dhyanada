"""Seed rules for the advisory engine (Phase 4 Step 3).

Run as:
    python -m src.advisory.seed_rules
"""
from __future__ import annotations

import asyncio
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.advisory.models import RuleData
from src.advisory.repository import AdvisoryRepository
from src.config import settings


SEED_RULES: List[RuleData] = [
    # ------------------------------------------------------------------
    # DISEASE RULES
    # ------------------------------------------------------------------
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
        message_en="Humidity >90% with cool temperatures forecast for next 2+ days — high late blight risk.",
        action_hint="Apply preventive mancozeb 0.25% spray. Avoid overhead irrigation.",
        source_citation="ICAR-IIHR tomato advisory",
    ),
    RuleData(
        rule_key="late_blight_potato",
        advisory_type="disease",
        crop="potato",
        min_humidity_pct=90,
        min_temp_c=10,
        max_temp_c=24,
        consecutive_days=2,
        risk_level="high",
        title_en="Late blight risk on potato",
        message_en="Humidity >90% with cool temperatures forecast — late blight can spread rapidly.",
        action_hint="Spray chlorothalonil or mancozeb preventively. Remove infected plant debris.",
        source_citation="ICAR-CPRI potato advisory",
    ),
    RuleData(
        rule_key="purple_blotch_onion",
        advisory_type="disease",
        crop="onion",
        min_humidity_pct=80,
        min_temp_c=20,
        max_temp_c=30,
        consecutive_days=2,
        risk_level="high",
        title_en="Purple blotch risk on onion",
        message_en="Humid, warm conditions for 2+ days favor purple blotch fungus on onion foliage.",
        action_hint="Apply mancozeb or tebuconazole spray. Ensure good field drainage.",
        source_citation="ICAR-DOGR onion advisory",
    ),
    RuleData(
        rule_key="downy_mildew_grape",
        advisory_type="disease",
        crop="grape",
        min_humidity_pct=75,
        min_rainfall_mm=5,
        min_temp_c=18,
        max_temp_c=26,
        risk_level="high",
        title_en="Downy mildew risk on grape",
        message_en="Humid + rainy forecast in 18–26°C range — downy mildew infection window.",
        action_hint="Apply metalaxyl or copper oxychloride spray. Prune dense canopy for airflow.",
        source_citation="ICAR-NRC Grapes advisory",
    ),
    RuleData(
        rule_key="blast_paddy",
        advisory_type="disease",
        crop="paddy",
        min_humidity_pct=90,
        min_temp_c=22,
        max_temp_c=28,
        consecutive_days=2,
        risk_level="high",
        title_en="Rice blast risk",
        message_en="Night humidity near saturation with mild temps favors Magnaporthe blast fungus.",
        action_hint="Apply tricyclazole preventively. Avoid excess nitrogen fertilizer.",
        source_citation="ICAR-IIRR paddy advisory",
    ),
    RuleData(
        rule_key="rust_wheat",
        advisory_type="disease",
        crop="wheat",
        min_humidity_pct=80,
        min_temp_c=15,
        max_temp_c=22,
        consecutive_days=2,
        risk_level="medium",
        title_en="Wheat rust risk",
        message_en="Cool, humid spell forecast — conducive for yellow/brown rust development.",
        action_hint="Scout for rust pustules. Apply propiconazole at first sign of infection.",
        source_citation="ICAR-IIWBR wheat advisory",
    ),
    RuleData(
        rule_key="tikka_groundnut",
        advisory_type="disease",
        crop="groundnut",
        min_humidity_pct=80,
        min_temp_c=25,
        max_temp_c=30,
        consecutive_days=2,
        risk_level="medium",
        title_en="Tikka leaf spot risk on groundnut",
        message_en="Warm, humid forecast promotes Cercospora tikka leaf spot on groundnut.",
        action_hint="Apply carbendazim or mancozeb spray. Ensure 45-day spray schedule.",
        source_citation="ICAR-DGR groundnut advisory",
    ),
    RuleData(
        rule_key="powdery_mildew_grape",
        advisory_type="disease",
        crop="grape",
        min_humidity_pct=60,
        max_humidity_pct=80,
        min_temp_c=20,
        max_temp_c=27,
        risk_level="medium",
        title_en="Powdery mildew risk on grape",
        message_en="Moderate humidity + warm temps favor powdery mildew on grape vines.",
        action_hint="Apply sulphur dust or wettable sulphur. Avoid over-irrigation.",
        source_citation="ICAR-NRC Grapes advisory",
    ),
    RuleData(
        rule_key="fruit_rot_chilli",
        advisory_type="disease",
        crop="chilli",
        min_humidity_pct=85,
        min_rainfall_mm=10,
        min_temp_c=22,
        max_temp_c=30,
        risk_level="high",
        title_en="Anthracnose fruit rot risk on chilli",
        message_en="Humid + rainy forecast — high risk of Colletotrichum fruit rot on chilli.",
        action_hint="Apply azoxystrobin spray. Harvest mature fruits promptly.",
        source_citation="ICAR-IIHR chilli advisory",
    ),

    # ------------------------------------------------------------------
    # IRRIGATION RULES
    # ------------------------------------------------------------------
    RuleData(
        rule_key="heat_irrigation_general",
        advisory_type="irrigation",
        crop=None,
        min_temp_c=38,
        consecutive_days=2,
        max_rainfall_mm=5,
        risk_level="medium",
        title_en="Alternate-day watering recommended",
        message_en="Max temp forecast >38°C for 2+ days with no rain — crop water-stress likely.",
        action_hint="Irrigate early morning on alternate days. Mulch to reduce evaporation.",
        source_citation="FAO Irrigation Manual Module 4",
    ),
    RuleData(
        rule_key="heat_wave_sugarcane",
        advisory_type="irrigation",
        crop="sugarcane",
        min_temp_c=35,
        consecutive_days=3,
        max_rainfall_mm=5,
        risk_level="high",
        title_en="Deep irrigation needed for sugarcane",
        message_en="3+ days of >35°C with no rain — sugarcane leaves will curl from water stress.",
        action_hint="Apply 60mm deep irrigation. Consider trash mulching between rows.",
        source_citation="ICAR-SBI sugarcane advisory",
    ),
    RuleData(
        rule_key="heat_onion_frequent",
        advisory_type="irrigation",
        crop="onion",
        min_temp_c=35,
        consecutive_days=2,
        max_rainfall_mm=5,
        risk_level="medium",
        title_en="Frequent light irrigation for onion",
        message_en="Hot spell forecast — onion has shallow roots and needs more frequent watering.",
        action_hint="Switch to daily light irrigation (20mm). Avoid dry spells >2 days.",
        source_citation="ICAR-DOGR onion advisory",
    ),
    RuleData(
        rule_key="heat_wheat_grain_fill",
        advisory_type="irrigation",
        crop="wheat",
        min_temp_c=32,
        consecutive_days=2,
        max_rainfall_mm=5,
        risk_level="medium",
        title_en="Critical irrigation at wheat grain-fill",
        message_en="Temps >32°C during grain-fill reduce yield — ensure soil moisture is maintained.",
        action_hint="Irrigate to bring field capacity up. Do not skip scheduled irrigation.",
        source_citation="ICAR-IIWBR wheat advisory",
    ),
    RuleData(
        rule_key="skip_irrigation_rain",
        advisory_type="irrigation",
        crop=None,
        min_rainfall_mm=25,
        risk_level="low",
        title_en="Skip planned irrigation",
        message_en="Heavy rain (>25mm) expected in next 48h — soil will be saturated.",
        action_hint="Skip scheduled irrigation to avoid waterlogging and root rot.",
        source_citation="FAO Irrigation Manual Module 4",
    ),

    # ------------------------------------------------------------------
    # WEATHER / ACTION RULES
    # ------------------------------------------------------------------
    RuleData(
        rule_key="heavy_rain_spray_warning",
        advisory_type="weather",
        crop=None,
        min_rainfall_mm=15,
        risk_level="medium",
        title_en="Avoid pesticide spraying",
        message_en="Significant rain (>15mm) expected — pesticide wash-off will waste application.",
        action_hint="Postpone spraying until rain clears and foliage dries. Cover stored fertilizer.",
        source_citation="IMD farmer bulletin",
    ),
    RuleData(
        rule_key="heavy_rain_harvest_warning",
        advisory_type="weather",
        crop=None,
        min_rainfall_mm=40,
        risk_level="high",
        title_en="Harvest mature crops before heavy rain",
        message_en="Very heavy rain (>40mm) forecast — standing mature crops risk lodging and spoilage.",
        action_hint="Harvest any ready crops today. Ensure stored produce is covered and dry.",
        source_citation="IMD severe-weather advisory",
    ),
    RuleData(
        rule_key="cold_wave_vegetable",
        advisory_type="weather",
        crop=None,
        max_temp_c=10,
        consecutive_days=2,
        risk_level="medium",
        title_en="Cold wave — protect sensitive crops",
        message_en="Forecast minimum <10°C for 2+ days can damage tomato, chilli, brinjal.",
        action_hint="Cover nursery beds at night. Light irrigation helps raise night temperature.",
        source_citation="IMD cold-wave bulletin",
    ),
    RuleData(
        rule_key="heat_wave_general",
        advisory_type="weather",
        crop=None,
        min_temp_c=42,
        risk_level="high",
        title_en="Extreme heat wave alert",
        message_en="Forecast max >42°C — severe heat stress risk on crops and livestock.",
        action_hint="Ensure water availability. Shade nursery seedlings. Schedule field work before 10 AM.",
        source_citation="IMD heat-wave bulletin",
    ),

    # ------------------------------------------------------------------
    # PEST RULES
    # ------------------------------------------------------------------
    RuleData(
        rule_key="bollworm_cotton",
        advisory_type="pest",
        crop="cotton",
        min_temp_c=25,
        max_temp_c=35,
        max_rainfall_mm=10,
        risk_level="medium",
        title_en="Bollworm pressure likely on cotton",
        message_en="Warm, dry conditions favor bollworm build-up on cotton bolls.",
        action_hint="Scout fields weekly. Install pheromone traps. Spray emamectin benzoate if threshold exceeded.",
        source_citation="ICAR-CICR cotton advisory",
    ),
    RuleData(
        rule_key="aphid_mustard",
        advisory_type="pest",
        crop="mustard",
        min_temp_c=15,
        max_temp_c=25,
        max_rainfall_mm=5,
        risk_level="medium",
        title_en="Aphid risk on mustard",
        message_en="Cool, dry forecast is ideal for mustard aphid population growth.",
        action_hint="Spray imidacloprid or dimethoate at first sign. Favour early-morning application.",
        source_citation="ICAR-DRMR mustard advisory",
    ),
    RuleData(
        rule_key="whitefly_general",
        advisory_type="pest",
        crop=None,
        min_temp_c=28,
        max_rainfall_mm=5,
        consecutive_days=3,
        risk_level="medium",
        title_en="Whitefly build-up risk",
        message_en="Hot, dry spell favors whitefly — vector of several viral diseases.",
        action_hint="Install yellow sticky traps. Spray neem-based insecticide at threshold.",
        source_citation="ICAR-NBAIR pest advisory",
    ),
]


async def load_seed_rules() -> None:
    """Upsert all seed rules into the advisory_rules table."""
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        repo = AdvisoryRepository(session)
        inserted = updated = 0
        for rule in SEED_RULES:
            existing = await repo.get_rule_by_key(rule.rule_key)
            await repo.upsert_rule(rule)
            if existing:
                updated += 1
            else:
                inserted += 1
        print(f"Seed rules loaded: {inserted} inserted, {updated} updated, {len(SEED_RULES)} total.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_seed_rules())
