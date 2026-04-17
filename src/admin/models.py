"""Admin dashboard data models."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class DailyStats:
    """Daily activity snapshot."""
    date: str  # ISO format YYYY-MM-DD
    dau: int  # Daily active users
    messages_inbound: int
    messages_outbound: int
    top_intent: Optional[str] = None
    top_intent_count: int = 0


@dataclass
class CropStat:
    """Crop query volume ranking."""
    commodity: str
    count: int
    district: Optional[str] = None


@dataclass
class SubscriptionFunnel:
    """Subscription state breakdown."""
    new: int  # onboarding_state = 'NEW'
    awaiting_consent: int  # onboarding_state = 'AWAITING_CONSENT'
    active: int  # subscription_status = 'ACTIVE'
    opted_out: int  # subscription_status = 'NONE' + onboarding_state = 'OPTED_OUT'
    total_farmers: int


@dataclass
class MessageLogEntry:
    """Anonymized message log for dashboard display."""
    timestamp: datetime
    farmer_phone_masked: str  # last 4 digits only, e.g. "****8765"
    direction: str  # 'inbound' | 'outbound'
    message_preview: str  # first 60 chars
    detected_intent: Optional[str]
    detected_entities: dict  # e.g. {'commodity': 'onion', 'district': 'pune'}


@dataclass
class BroadcastHealth:
    """Celery broadcast task health."""
    last_run_at: Optional[datetime]
    status: str  # 'success' | 'partial_failure' | 'failure' | 'pending'
    sent_count: int
    failed_count: int
    partial_failures: List[str]  # list of farmer phones with errors


@dataclass
class AdminDashboardData:
    """Complete dashboard snapshot."""
    dau_today: int
    messages_today: int
    total_farmers: int
    active_farmers: int
    daily_stats_7d: List[DailyStats]
    top_crops: List[CropStat]
    funnel: SubscriptionFunnel
    recent_messages: List[MessageLogEntry]
    broadcast_health: Optional[BroadcastHealth]
    generated_at: datetime
