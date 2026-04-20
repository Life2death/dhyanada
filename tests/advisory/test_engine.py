"""Unit tests for the advisory engine — pure rule-evaluation logic.

These tests avoid the DB entirely by exercising `aggregate_weather` and
`rule_matches` with synthetic inputs.
"""
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.advisory.engine import aggregate_weather, rule_matches, _longest_streak


def _wx_obs(d: date, metric: str, value: float, min_v: float = None, max_v: float = None):
    """Build a stand-in for WeatherObservation with just the fields the engine reads."""
    return SimpleNamespace(
        date=d,
        metric=metric,
        value=Decimal(str(value)),
        min_value=Decimal(str(min_v)) if min_v is not None else None,
        max_value=Decimal(str(max_v)) if max_v is not None else None,
    )


def _rule(**kwargs):
    defaults = dict(
        rule_key="test",
        advisory_type="disease",
        crop=None,
        eligible_districts=None,
        min_temp_c=None,
        max_temp_c=None,
        min_humidity_pct=None,
        max_humidity_pct=None,
        min_rainfall_mm=None,
        max_rainfall_mm=None,
        consecutive_days=1,
        risk_level="medium",
        title_en="",
        message_en="",
        action_hint="",
        source_citation=None,
        active=True,
    )
    defaults.update(kwargs)
    # Wrap numeric thresholds in Decimal where present, matching ORM behavior
    for f in (
        "min_temp_c",
        "max_temp_c",
        "min_humidity_pct",
        "max_humidity_pct",
        "min_rainfall_mm",
        "max_rainfall_mm",
    ):
        if defaults[f] is not None:
            defaults[f] = Decimal(str(defaults[f]))
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# _longest_streak
# ---------------------------------------------------------------------------


def test_longest_streak_empty():
    assert _longest_streak([]) == 0


def test_longest_streak_all_false():
    assert _longest_streak([False, False, False]) == 0


def test_longest_streak_mixed():
    assert _longest_streak([True, True, False, True, True, True, False]) == 3


def test_longest_streak_all_true():
    assert _longest_streak([True] * 5) == 5


# ---------------------------------------------------------------------------
# aggregate_weather
# ---------------------------------------------------------------------------


def test_aggregate_empty():
    wx = aggregate_weather([])
    assert wx.forecast_window_days == 0
    assert wx.max_temp_c == 0.0
    assert wx.total_rainfall_mm == 0.0


def test_aggregate_disease_window_humid_cool():
    """Three consecutive days at 92% RH + 22°C should flag disease streak."""
    today = date.today()
    obs = []
    for i in range(3):
        d = today + timedelta(days=i)
        obs.append(_wx_obs(d, "temperature", 22.0, min_v=18.0, max_v=22.0))
        obs.append(_wx_obs(d, "humidity", 92.0))

    wx = aggregate_weather(obs)
    assert wx.forecast_window_days == 3
    assert wx.max_humidity_pct == pytest.approx(92.0)
    assert wx.consecutive_high_humidity_days == 3
    assert wx.consecutive_hot_days == 0
    assert wx.max_temp_c == 22.0


def test_aggregate_hot_streak():
    """Consecutive days with max T > 35 should count as hot streak."""
    today = date.today()
    obs = []
    for i in range(4):
        d = today + timedelta(days=i)
        obs.append(_wx_obs(d, "temperature", 40.0, min_v=28.0, max_v=40.0))
        obs.append(_wx_obs(d, "humidity", 40.0))
    wx = aggregate_weather(obs)
    assert wx.consecutive_hot_days == 4
    assert wx.consecutive_high_humidity_days == 0


def test_aggregate_rainfall_summed():
    today = date.today()
    obs = [
        _wx_obs(today, "rainfall", 10.0),
        _wx_obs(today + timedelta(days=1), "rainfall", 25.0),
        _wx_obs(today + timedelta(days=2), "rainfall", 5.0),
    ]
    wx = aggregate_weather(obs)
    assert wx.total_rainfall_mm == pytest.approx(40.0)


# ---------------------------------------------------------------------------
# rule_matches — positive cases
# ---------------------------------------------------------------------------


def _late_blight_wx():
    today = date.today()
    obs = []
    for i in range(2):
        d = today + timedelta(days=i)
        obs.append(_wx_obs(d, "temperature", 22.0, min_v=18.0, max_v=22.0))
        obs.append(_wx_obs(d, "humidity", 92.0))
    return aggregate_weather(obs)


def test_rule_matches_late_blight_fires():
    rule = _rule(
        advisory_type="disease",
        crop="tomato",
        min_humidity_pct=90,
        min_temp_c=10,
        max_temp_c=24,
        consecutive_days=2,
        risk_level="high",
    )
    wx = _late_blight_wx()
    assert rule_matches(rule, wx, ["tomato", "onion"], "pune") is True


def test_rule_matches_wrong_crop_skipped():
    rule = _rule(crop="tomato", min_humidity_pct=90, consecutive_days=2)
    wx = _late_blight_wx()
    assert rule_matches(rule, wx, ["wheat"], "pune") is False


def test_rule_matches_district_gate():
    rule = _rule(crop="tomato", eligible_districts=["nashik"], min_humidity_pct=90, consecutive_days=2)
    wx = _late_blight_wx()
    assert rule_matches(rule, wx, ["tomato"], "pune") is False
    assert rule_matches(rule, wx, ["tomato"], "Nashik") is True  # case-insensitive


def test_rule_matches_neutral_weather_skipped():
    """Moderate 26°C, 60% RH, 0mm rain should NOT trigger disease rules."""
    today = date.today()
    obs = []
    for i in range(5):
        d = today + timedelta(days=i)
        obs.append(_wx_obs(d, "temperature", 26.0, min_v=22.0, max_v=28.0))
        obs.append(_wx_obs(d, "humidity", 60.0))
    wx = aggregate_weather(obs)
    rule = _rule(crop="tomato", min_humidity_pct=90, consecutive_days=2)
    assert rule_matches(rule, wx, ["tomato"], "pune") is False


def test_rule_matches_irrigation_heat_streak():
    today = date.today()
    obs = []
    for i in range(3):
        d = today + timedelta(days=i)
        obs.append(_wx_obs(d, "temperature", 40.0, min_v=28.0, max_v=40.0))
        obs.append(_wx_obs(d, "humidity", 40.0))
    wx = aggregate_weather(obs)
    rule = _rule(
        advisory_type="irrigation",
        min_temp_c=38,
        consecutive_days=2,
        max_rainfall_mm=5,
        risk_level="medium",
    )
    assert rule_matches(rule, wx, ["wheat"], "pune") is True


def test_rule_matches_skip_irrigation_on_rain():
    today = date.today()
    obs = [
        _wx_obs(today, "rainfall", 30.0),
        _wx_obs(today + timedelta(days=1), "rainfall", 10.0),
        _wx_obs(today, "temperature", 28.0, min_v=24.0, max_v=30.0),
    ]
    wx = aggregate_weather(obs)
    rule = _rule(
        advisory_type="irrigation",
        min_rainfall_mm=25,
        risk_level="low",
    )
    assert rule_matches(rule, wx, ["wheat"], "pune") is True


def test_rule_matches_insufficient_consecutive_days():
    """Single day of high humidity should NOT trigger a 2-day consecutive rule."""
    today = date.today()
    obs = [
        _wx_obs(today, "temperature", 22.0, min_v=18.0, max_v=22.0),
        _wx_obs(today, "humidity", 92.0),
        _wx_obs(today + timedelta(days=1), "temperature", 22.0, min_v=18.0, max_v=22.0),
        _wx_obs(today + timedelta(days=1), "humidity", 60.0),  # breaks streak
    ]
    wx = aggregate_weather(obs)
    rule = _rule(
        advisory_type="disease",
        crop="tomato",
        min_humidity_pct=90,
        consecutive_days=2,
    )
    assert rule_matches(rule, wx, ["tomato"], "pune") is False
