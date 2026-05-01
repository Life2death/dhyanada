"""Rule-based advisory engine (Phase 4 Step 3).

Pure-function core: given a set of WeatherObservation rows + a farmer's crops +
district + a list of AdvisoryRule rows, produce Advisory records to persist.

Usage:
    from src.advisory.engine import generate_for_farmer
    created = await generate_for_farmer(db, farmer_id=1)
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.advisory.models import WeatherAggregate
from src.models.advisory import Advisory
from src.models.advisory_rule import AdvisoryRule
from src.models.farmer import CropOfInterest, Farmer
from src.models.weather import WeatherObservation


# ---------------------------------------------------------------------------
# Pure logic
# ---------------------------------------------------------------------------


def aggregate_weather(observations: Iterable[WeatherObservation]) -> WeatherAggregate:
    """Collapse a window of WeatherObservation rows into a single summary.

    Groups by (date, metric) — for each day picks max of value for temperature-like
    metrics, sum for rainfall, avg for humidity. Computes consecutive-day streaks
    for high humidity (avg RH > 85) and high heat (max T > 35).
    """
    by_day_metric: dict[tuple[date, str], list[float]] = defaultdict(list)
    day_max_temp: dict[date, float] = {}
    day_min_temp: dict[date, float] = {}

    for obs in observations:
        value = float(obs.value) if obs.value is not None else 0.0
        by_day_metric[(obs.date, obs.metric)].append(value)
        # Prefer explicit min/max columns when present
        if obs.metric == "temperature":
            hi = float(obs.max_value) if obs.max_value is not None else value
            lo = float(obs.min_value) if obs.min_value is not None else value
            day_max_temp[obs.date] = max(day_max_temp.get(obs.date, hi), hi)
            day_min_temp[obs.date] = min(day_min_temp.get(obs.date, lo), lo)

    days = sorted({d for (d, _m) in by_day_metric.keys()})

    # Temperature
    temps = list(day_max_temp.values())
    mins = list(day_min_temp.values())
    max_temp = max(temps) if temps else 0.0
    min_temp = min(mins) if mins else 0.0
    avg_temp = sum(temps) / len(temps) if temps else 0.0

    # Humidity (avg per day, then max + overall avg)
    daily_humidity: list[float] = []
    for d in days:
        vals = by_day_metric.get((d, "humidity"), [])
        if vals:
            daily_humidity.append(sum(vals) / len(vals))
    max_humidity = max(daily_humidity) if daily_humidity else 0.0
    avg_humidity = sum(daily_humidity) / len(daily_humidity) if daily_humidity else 0.0

    # Rainfall — total across window
    total_rainfall = 0.0
    for d in days:
        total_rainfall += sum(by_day_metric.get((d, "rainfall"), []))

    # Streaks: iterate days in order
    consec_humid = _longest_streak(
        [(sum(by_day_metric.get((d, "humidity"), [])) / max(1, len(by_day_metric.get((d, "humidity"), [])))) > 85 for d in days]
    )
    consec_hot = _longest_streak([day_max_temp.get(d, 0.0) > 35 for d in days])

    return WeatherAggregate(
        max_temp_c=max_temp,
        min_temp_c=min_temp,
        avg_temp_c=avg_temp,
        avg_humidity_pct=avg_humidity,
        max_humidity_pct=max_humidity,
        total_rainfall_mm=total_rainfall,
        consecutive_high_humidity_days=consec_humid,
        consecutive_hot_days=consec_hot,
        forecast_window_days=len(days),
    )


def _longest_streak(flags: list[bool]) -> int:
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        if cur > best:
            best = cur
    return best


def rule_matches(
    rule: AdvisoryRule,
    wx: WeatherAggregate,
    farmer_crops: list[str],
    district: Optional[str],
) -> bool:
    """Return True if the rule's thresholds are all satisfied by the aggregate."""
    # Crop gate
    if rule.crop and rule.crop.lower() not in [c.lower() for c in farmer_crops]:
        return False

    # District gate
    if rule.eligible_districts:
        if not district:
            return False
        allowed = [d.lower() for d in rule.eligible_districts]
        if district.lower() not in allowed:
            return False

    def ge(val: Optional[Decimal], floor: float) -> bool:
        return val is None or floor >= float(val)

    def le(val: Optional[Decimal], ceil: float) -> bool:
        return val is None or ceil <= float(val)

    # Humidity
    if not ge(rule.min_humidity_pct, wx.max_humidity_pct):
        return False
    if not le(rule.max_humidity_pct, wx.avg_humidity_pct):
        return False

    # Temperature — checked against window max (heat signal) and min (cold signal)
    if rule.min_temp_c is not None and wx.max_temp_c < float(rule.min_temp_c):
        return False
    if rule.max_temp_c is not None and wx.min_temp_c > float(rule.max_temp_c):
        return False

    # Rainfall
    if not ge(rule.min_rainfall_mm, wx.total_rainfall_mm):
        return False
    if not le(rule.max_rainfall_mm, wx.total_rainfall_mm):
        return False

    # Consecutive-day gate
    if rule.consecutive_days > 1:
        if rule.advisory_type == "disease":
            if wx.consecutive_high_humidity_days < rule.consecutive_days:
                return False
        elif rule.advisory_type == "irrigation":
            if wx.consecutive_hot_days < rule.consecutive_days:
                return False
        # weather/pest types: skip streak enforcement (too varied)

    return True


# ---------------------------------------------------------------------------
# DB-backed orchestration
# ---------------------------------------------------------------------------


async def _load_forecast(
    db: AsyncSession, district: str, days_ahead: int = 7
) -> list[WeatherObservation]:
    today = date.today()
    stmt = (
        select(WeatherObservation)
        .where(
            and_(
                WeatherObservation.district == district,
                WeatherObservation.date >= today,
                WeatherObservation.date <= today + timedelta(days=days_ahead),
            )
        )
        .order_by(WeatherObservation.date, WeatherObservation.metric)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _load_farmer_crops(db: AsyncSession, farmer_id: int) -> list[str]:
    stmt = select(CropOfInterest.crop).where(CropOfInterest.farmer_id == farmer_id).distinct()
    result = await db.execute(stmt)
    return [c for c in result.scalars().all() if c]


async def _load_active_rules(db: AsyncSession) -> list[AdvisoryRule]:
    stmt = select(AdvisoryRule).where(AdvisoryRule.active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _advisory_exists(
    db: AsyncSession, farmer_id: int, rule_id: int, advisory_date: date
) -> bool:
    stmt = select(Advisory.id).where(
        and_(
            Advisory.farmer_id == farmer_id,
            Advisory.rule_id == rule_id,
            Advisory.advisory_date == advisory_date,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _build_advisory(
    rule: AdvisoryRule,
    farmer_id: int,
    wx: WeatherAggregate,
    farmer_crops: list[str],
    district: str,
) -> Advisory:
    today = date.today()
    # Pick crop from farmer's list when rule is crop-agnostic
    crop = rule.crop or (farmer_crops[0] if farmer_crops else None)

    # Enrich with AI insights (optional; fails gracefully)
    from src.advisory.ai_enrichment import enrich_advisory_with_ai
    ai_insights = await enrich_advisory_with_ai(
        rule_type=rule.advisory_type,
        farmer_crops=farmer_crops,
        max_temp_c=wx.max_temp_c,
        min_temp_c=wx.min_temp_c,
        avg_humidity_pct=wx.avg_humidity_pct,
        total_rainfall_mm=wx.total_rainfall_mm,
        consecutive_high_humidity_days=wx.consecutive_high_humidity_days,
        district=district,
    )

    return Advisory(
        farmer_id=farmer_id,
        rule_id=rule.id,
        crop=crop,
        advisory_date=today,
        valid_until=today + timedelta(days=max(1, wx.forecast_window_days)),
        risk_level=rule.risk_level,
        title=rule.title_en,
        message=rule.message_en,
        action_hint=rule.action_hint,
        source_citation=rule.source_citation,
        ai_insights=ai_insights,
        delivered_via={"dashboard": True},
    )


async def generate_for_farmer(db: AsyncSession, farmer_id: int) -> list[Advisory]:
    """Evaluate all active rules for one farmer, persist new advisories, return them."""
    farmer = (await db.execute(select(Farmer).where(Farmer.id == farmer_id))).scalar_one_or_none()
    if not farmer:
        return []

    district = farmer.district
    crops = await _load_farmer_crops(db, farmer_id)
    if not district:
        return []

    forecast = await _load_forecast(db, district)
    if not forecast:
        return []

    wx = aggregate_weather(forecast)
    rules = await _load_active_rules(db)

    created: list[Advisory] = []
    today = date.today()
    for rule in rules:
        if not rule_matches(rule, wx, crops, district):
            continue
        if await _advisory_exists(db, farmer_id, rule.id, today):
            continue
        adv = await _build_advisory(rule, farmer_id, wx, crops, district)
        db.add(adv)
        created.append(adv)

    if created:
        await db.commit()
        for adv in created:
            await db.refresh(adv)
    return created


async def generate_for_all_farmers(db: AsyncSession) -> dict[int, int]:
    """Run the engine for every farmer that has a district + at least one crop.

    Returns: {farmer_id: advisories_created_count}
    """
    stmt = select(Farmer.id).where(Farmer.district.is_not(None), Farmer.deleted_at.is_(None))
    result = await db.execute(stmt)
    farmer_ids = list(result.scalars().all())

    counts: dict[int, int] = {}
    for fid in farmer_ids:
        created = await generate_for_farmer(db, fid)
        counts[fid] = len(created)
    return counts
