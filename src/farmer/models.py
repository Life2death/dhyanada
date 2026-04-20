"""Data classes for farmer dashboard responses."""

from datetime import date, datetime
from typing import Any, List, Optional
from pydantic import BaseModel


class PriceData(BaseModel):
    """Price information for a crop."""
    crop: str
    latest_price: Optional[float]
    min_price_30d: Optional[float]
    max_price_30d: Optional[float]
    avg_price_30d: Optional[float]
    msp: Optional[float]
    price_trend: str  # "up", "down", "stable"
    pct_change_7d: float
    alert: Optional[dict] = None  # {"type": "price_drop", "message": "..."}


class WeatherForecastDay(BaseModel):
    """Weather forecast for a single day."""
    date: str
    day: str  # "Mon", "Tue", etc.
    high: float
    low: float
    condition: str  # "Sunny", "Rainy", etc.
    precipitation_mm: float
    humidity_pct: float


class WeatherData(BaseModel):
    """Weather information for farmer's district."""
    district: str
    current_temp: Optional[float]
    forecast_5d: List[WeatherForecastDay]


class SchemeData(BaseModel):
    """Government scheme information."""
    id: int
    name: str
    eligible: bool
    description: str
    min_hectares: Optional[float]
    max_hectares: Optional[float]
    amount_per_acre: Optional[float]
    details_url: Optional[str]


class FarmerStats(BaseModel):
    """Statistics about farmer's interactions."""
    queries_asked: int
    queries_answered: int
    messages_received: int
    messages_sent: int
    last_query_at: Optional[datetime]


class FarmerInfo(BaseModel):
    """Basic farmer information."""
    name: Optional[str]
    district: Optional[str]
    land_hectares: Optional[float]
    plan_tier: str
    preferred_language: str


class AdvisoryCard(BaseModel):
    """Advisory card shown on farmer dashboard."""
    id: int
    advisory_type: Optional[str] = None  # disease | irrigation | weather | pest
    crop: Optional[str]
    advisory_date: date
    valid_until: date
    risk_level: str  # low | medium | high
    title: str
    message: str
    action_hint: str
    source_citation: Optional[str] = None


class FarmerDashboardData(BaseModel):
    """Complete farmer dashboard data."""
    farmer: FarmerInfo
    crops: List[dict]  # [{"crop": "onion", "count_following": 1}]
    prices: List[PriceData]
    weather: WeatherData
    schemes: List[SchemeData]
    advisories: List[AdvisoryCard] = []
    stats: FarmerStats
    generated_at: datetime


class LoginRequestPayload(BaseModel):
    """OTP login request."""
    phone: str  # International format: +91XXXXXXXXXX


class LoginVerifyPayload(BaseModel):
    """OTP verification request."""
    phone: str
    otp: str  # 6-digit OTP


class LoginResponse(BaseModel):
    """OTP login response."""
    success: bool
    message: str
    token: Optional[str] = None
