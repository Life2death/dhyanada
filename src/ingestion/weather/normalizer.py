"""Normalize weather metric names and location slugs to canonical forms."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DATA_FILE = Path(__file__).parent / "data" / "maharashtra_talukas.json"

# Map raw metric names from APIs → canonical metric slugs
_METRIC_ALIASES = {
    "temperature": "temperature",
    "temp": "temperature",
    "temperature_max": "temperature",
    "temperature_min": "temperature",
    "temp_max": "temperature",
    "temp_min": "temperature",
    "max_temp": "temperature",
    "min_temp": "temperature",
    "तापमान": "temperature",
    "तापमान_उच्च": "temperature",
    "तापमान_न्यून": "temperature",
    "rainfall": "rainfall",
    "rain": "rainfall",
    "precipitation": "rainfall",
    "1h": "rainfall",
    "rain_1h": "rainfall",
    "पाऊस": "rainfall",
    "humidity": "humidity",
    "relative_humidity": "humidity",
    "humidity_max": "humidity",
    "humidity_min": "humidity",
    "ओलावा": "humidity",
    "wind_speed": "wind_speed",
    "wind": "wind_speed",
    "speed": "wind_speed",
    "wind_spd": "wind_speed",
    "वारा_वेग": "wind_speed",
    "वारा": "wind_speed",
    "wind_direction": "wind_direction",
    "wind_deg": "wind_direction",
    "wind_dir": "wind_direction",
    "pressure": "pressure",
    "press": "pressure",
    "barometric_pressure": "pressure",
    "clouds": "cloud_cover",
    "cloud_coverage": "cloud_cover",
    "cloudiness": "cloud_cover",
}

CANONICAL_METRICS = {
    "temperature", "rainfall", "humidity",
    "wind_speed", "wind_direction", "pressure", "cloud_cover",
}

# Legacy district-level aliases (kept for backward compatibility)
_DISTRICT_ALIASES: dict[str, str] = {
    "pune": "pune",
    "पुणे": "pune",
    "nashik": "nashik",
    "नाशिक": "nashik",
    "ahilyanagar": "ahilyanagar",
    "ahmednagar": "ahilyanagar",
    "अहमदनगर": "ahilyanagar",
    "navi_mumbai": "navi_mumbai",
    "navimumbai": "navi_mumbai",
    "नवी_मुंबई": "navi_mumbai",
    "mumbai": "mumbai",
    "मुंबई": "mumbai",
}


@lru_cache(maxsize=1)
def _taluka_set() -> set[str]:
    """Return the set of all canonical taluka slugs (loaded once)."""
    with _DATA_FILE.open() as f:
        data = json.load(f)
    return {entry["taluka"] for entry in data}


@lru_cache(maxsize=1)
def _district_for_taluka() -> dict[str, str]:
    """Return mapping taluka_slug → district_slug."""
    with _DATA_FILE.open() as f:
        data = json.load(f)
    return {entry["taluka"]: entry["district"] for entry in data}


def normalize_metric(raw: str) -> Optional[str]:
    """Normalize raw metric name to canonical slug."""
    if not raw:
        return None
    return _METRIC_ALIASES.get(raw.lower().strip())


def normalize_taluka(raw: str) -> Optional[str]:
    """Normalize a taluka name to its canonical slug.

    Accepts the exact slug from the data file (lowercase, underscores).
    Returns None for unrecognized values so the orchestrator can skip them.
    """
    if not raw:
        return None
    lower = raw.lower().strip()
    return lower if lower in _taluka_set() else None


def normalize_apmc(raw: str) -> Optional[str]:
    """Normalize a location identifier to a canonical slug.

    Accepts both taluka slugs (new) and legacy district codes (old).
    Returns None if unrecognized.
    """
    if not raw:
        return None

    lower = raw.lower().strip()

    # Try taluka set first (new records)
    if lower in _taluka_set():
        return lower

    # Fall back to legacy district aliases
    if raw in _DISTRICT_ALIASES:
        return _DISTRICT_ALIASES[raw]
    return _DISTRICT_ALIASES.get(lower)


def get_district_for_taluka(taluka: str) -> Optional[str]:
    """Return the parent district for a taluka slug."""
    return _district_for_taluka().get(taluka)


def normalize_unit(metric: str) -> str:
    """Return canonical unit string for a metric slug."""
    return {
        "temperature": "°C",
        "rainfall": "mm",
        "humidity": "%",
        "wind_speed": "km/h",
        "wind_direction": "degrees",
        "pressure": "hPa",
        "cloud_cover": "%",
    }.get(metric, "unknown")
