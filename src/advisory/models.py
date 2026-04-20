"""Pydantic models for the advisory engine (Phase 4 Step 3)."""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


@dataclass
class WeatherAggregate:
    """Aggregated weather signal derived from a 5–7 day forecast window."""
    max_temp_c: float
    min_temp_c: float
    avg_temp_c: float
    avg_humidity_pct: float
    max_humidity_pct: float
    total_rainfall_mm: float
    consecutive_high_humidity_days: int  # days where avg RH > 85
    consecutive_hot_days: int            # days where max T > 35
    forecast_window_days: int            # usually 5–7


class RuleData(BaseModel):
    """API representation of an AdvisoryRule."""
    id: Optional[int] = None
    rule_key: str
    advisory_type: str  # disease | irrigation | weather | pest
    crop: Optional[str] = None
    eligible_districts: Optional[List[str]] = None
    min_temp_c: Optional[float] = None
    max_temp_c: Optional[float] = None
    min_humidity_pct: Optional[float] = None
    max_humidity_pct: Optional[float] = None
    min_rainfall_mm: Optional[float] = None
    max_rainfall_mm: Optional[float] = None
    consecutive_days: int = 1
    risk_level: str = "medium"  # low | medium | high
    title_en: str
    message_en: str
    message_mr: Optional[str] = None
    action_hint: str
    source_citation: Optional[str] = None
    active: bool = True


class AdvisoryData(BaseModel):
    """Public representation of a generated Advisory, for dashboard / API."""
    id: int
    rule_id: int
    rule_key: Optional[str] = None
    advisory_type: Optional[str] = None
    crop: Optional[str] = None
    advisory_date: date
    valid_until: date
    risk_level: str
    title: str
    message: str
    action_hint: str
    source_citation: Optional[str] = None
    delivered_via: Optional[dict[str, Any]] = None
    dismissed_at: Optional[datetime] = None
    created_at: datetime


class AdvisoryGenerationResult(BaseModel):
    """Result of running the engine for one farmer."""
    farmer_id: int
    district: Optional[str]
    crops: List[str]
    advisories_created: int
    advisories_skipped_duplicate: int
    high_risk_count: int
    rules_evaluated: int
