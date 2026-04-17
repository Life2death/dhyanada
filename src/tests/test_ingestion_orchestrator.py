"""Orchestrator tests with stubbed sources — no network.

Covers:
- Parallel fetch + aggregation of multiple sources
- One source failing doesn't kill the batch
- Summary counts & healthy() reporting
- DB persistence is mocked — we only verify the orchestrator calls upsert
"""
from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ingestion.orchestrator import run_ingestion
from src.ingestion.sources.base import PriceRecord, PriceSource


class _StubSource(PriceSource):
    def __init__(self, name: str, records: list[PriceRecord], raises: Exception | None = None):
        self.name = name
        self._records = records
        self._raises = raises

    async def fetch(self, trade_date: date) -> list[PriceRecord]:
        if self._raises:
            raise self._raises
        return list(self._records)


def _rec(source: str, commodity: str = "tur", modal: str = "7500") -> PriceRecord:
    return PriceRecord(
        trade_date=date(2026, 4, 17),
        district="pune",
        apmc="pune_market_yard",
        mandi_display="Pune",
        commodity=commodity,
        modal_price=Decimal(modal),
        source=source,
    )


@pytest.mark.asyncio
async def test_orchestrator_aggregates_sources():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    sources = [
        _StubSource("agmarknet", [_rec("agmarknet", "tur"), _rec("agmarknet", "onion")]),
        _StubSource("msamb", [_rec("msamb", "tur")]),
    ]
    summary = await run_ingestion(date(2026, 4, 17), session, sources=sources)

    assert summary.per_source_counts == {"agmarknet": 2, "msamb": 1}
    assert summary.total_records == 3
    # winners: msamb-tur (msamb > agmarknet), agmarknet-onion (only one)
    assert summary.winner_count == 2
    assert summary.persisted == 3
    assert summary.errors == {}
    assert summary.healthy()


@pytest.mark.asyncio
async def test_one_source_failing_does_not_abort_batch():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    sources = [
        _StubSource("agmarknet", [_rec("agmarknet")]),
        _StubSource("msamb", [], raises=RuntimeError("site down")),
        _StubSource("nhrdf", [_rec("nhrdf", "onion")]),
    ]
    summary = await run_ingestion(date(2026, 4, 17), session, sources=sources)

    assert summary.per_source_counts == {"agmarknet": 1, "msamb": 0, "nhrdf": 1}
    assert "msamb" in summary.errors
    assert "site down" in summary.errors["msamb"]
    assert summary.total_records == 2
    assert summary.healthy(min_sources=2)  # 2 healthy sources


@pytest.mark.asyncio
async def test_unhealthy_when_only_one_source_returns_data():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    sources = [
        _StubSource("agmarknet", [_rec("agmarknet")]),
        _StubSource("msamb", []),
        _StubSource("nhrdf", [], raises=RuntimeError("boom")),
    ]
    summary = await run_ingestion(date(2026, 4, 17), session, sources=sources)

    assert not summary.healthy(min_sources=2)
