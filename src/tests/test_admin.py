"""Tests for admin dashboard module."""
from __future__ import annotations

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select, func

from src.admin.repository import AdminRepository
from src.admin.models import (
    DailyStats,
    CropStat,
    SubscriptionFunnel,
    MessageLogEntry,
    BroadcastHealth,
)


class TestDailyStats:
    """Tests for DailyStats model."""

    def test_daily_stats_creation(self):
        """Test DailyStats dataclass."""
        stats = DailyStats(
            date="2026-04-17",
            dau=42,
            messages_inbound=100,
            messages_outbound=50,
            top_intent="PRICE_QUERY",
            top_intent_count=75,
        )
        assert stats.date == "2026-04-17"
        assert stats.dau == 42
        assert stats.messages_inbound == 100
        assert stats.messages_outbound == 50


class TestCropStat:
    """Tests for CropStat model."""

    def test_crop_stat_creation(self):
        """Test CropStat dataclass."""
        crop = CropStat(
            commodity="onion",
            count=150,
            district="pune",
        )
        assert crop.commodity == "onion"
        assert crop.count == 150
        assert crop.district == "pune"


class TestSubscriptionFunnel:
    """Tests for SubscriptionFunnel model."""

    def test_funnel_creation(self):
        """Test SubscriptionFunnel dataclass."""
        funnel = SubscriptionFunnel(
            new=100,
            awaiting_consent=50,
            active=800,
            opted_out=20,
            total_farmers=970,
        )
        assert funnel.new == 100
        assert funnel.active == 800
        assert funnel.total_farmers == 970


class TestMessageLogEntry:
    """Tests for MessageLogEntry model."""

    def test_message_log_entry_creation(self):
        """Test MessageLogEntry dataclass."""
        msg = MessageLogEntry(
            timestamp=datetime.now(),
            farmer_phone_masked="****8765",
            direction="inbound",
            message_preview="कांदा दर",
            detected_intent="PRICE_QUERY",
            detected_entities={"commodity": "onion"},
        )
        assert msg.farmer_phone_masked == "****8765"
        assert msg.direction == "inbound"
        assert msg.detected_intent == "PRICE_QUERY"


class TestBroadcastHealth:
    """Tests for BroadcastHealth model."""

    def test_broadcast_health_success(self):
        """Test BroadcastHealth with success status."""
        health = BroadcastHealth(
            last_run_at=datetime.now(),
            status="success",
            sent_count=100,
            failed_count=0,
            partial_failures=[],
        )
        assert health.status == "success"
        assert health.sent_count == 100
        assert health.failed_count == 0

    def test_broadcast_health_partial_failure(self):
        """Test BroadcastHealth with partial failure."""
        health = BroadcastHealth(
            last_run_at=datetime.now(),
            status="partial_failure",
            sent_count=80,
            failed_count=20,
            partial_failures=["919876543210", "919876543211"],
        )
        assert health.status == "partial_failure"
        assert len(health.partial_failures) == 2


class TestAdminRepository:
    """Tests for AdminRepository query methods."""

    def test_admin_repository_initialization(self):
        """Test AdminRepository initialization."""
        mock_session = MagicMock()
        repo = AdminRepository(mock_session)
        assert repo.session == mock_session

    def test_admin_repository_has_all_methods(self):
        """Test that AdminRepository has all required methods."""
        mock_session = MagicMock()
        repo = AdminRepository(mock_session)

        # Verify all required methods exist
        assert hasattr(repo, "get_dau_today")
        assert hasattr(repo, "get_messages_today")
        assert hasattr(repo, "get_total_farmers")
        assert hasattr(repo, "get_active_farmers")
        assert hasattr(repo, "get_daily_stats_7d")
        assert hasattr(repo, "get_top_crops")
        assert hasattr(repo, "get_subscription_funnel")
        assert hasattr(repo, "get_recent_messages")
        assert hasattr(repo, "get_broadcast_health")
        assert hasattr(repo, "get_dashboard_data")

        # Verify methods are callable
        assert callable(repo.get_dau_today)
        assert callable(repo.get_messages_today)
        assert callable(repo.get_total_farmers)
        assert callable(repo.get_active_farmers)
        assert callable(repo.get_daily_stats_7d)
        assert callable(repo.get_top_crops)
        assert callable(repo.get_subscription_funnel)
        assert callable(repo.get_recent_messages)
        assert callable(repo.get_broadcast_health)
        assert callable(repo.get_dashboard_data)
