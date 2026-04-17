"""data.gov.in Agmarknet API source — the backbone feed.

Endpoint: https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070
Auth: API key query param (free, sign up at data.gov.in)
Format: JSON. ~500–2000 rows/day for Maharashtra.

Filters used server-side to keep payloads small:
- filters[state]=Maharashtra
- One request per target district (API filter is exact match on lowercase)

We don't filter by commodity — we fetch ALL commodities per district per the
user's "all commodities irrespective of district" directive.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import settings
from src.ingestion.normalizer import (
    TARGET_DISTRICTS,
    normalize_apmc,
    normalize_commodity,
    normalize_district,
)
from src.ingestion.sources.base import PriceRecord, PriceSource

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
_PAGE_LIMIT = 1000  # API max


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, "", "NA", "N/A", "-"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


class AgmarknetApiSource(PriceSource):
    name = "agmarknet"

    def __init__(self, api_key: Optional[str] = None, timeout_s: float = 30.0):
        self._api_key = api_key or settings.agmarknet_api_key
        self._timeout = timeout_s

    async def fetch(self, trade_date: date) -> list[PriceRecord]:
        if not self._api_key:
            logger.warning("agmarknet: no API key configured, skipping")
            return []

        records: list[PriceRecord] = []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            # One request per target district — small N, cleaner pagination
            for district_display in ("Pune", "Ahmednagar", "Thane", "Mumbai", "Nashik"):
                # Note: API still uses legacy "Ahmednagar". Our normalizer maps to ahilyanagar.
                # Thane covers Vashi APMC for Navi Mumbai.
                district_rows = await self._fetch_district(client, district_display, trade_date)
                records.extend(district_rows)

        logger.info("agmarknet: fetched %d records for %s", len(records), trade_date)
        return records

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _fetch_district(
        self,
        client: httpx.AsyncClient,
        district_display: str,
        trade_date: date,
    ) -> list[PriceRecord]:
        params = {
            "api-key": self._api_key,
            "format": "json",
            "limit": _PAGE_LIMIT,
            "filters[state]": "Maharashtra",
            "filters[district]": district_display,
            "filters[arrival_date]": trade_date.strftime("%d/%m/%Y"),
        }
        response = await client.get(_BASE_URL, params=params)
        response.raise_for_status()
        payload = response.json()

        rows = payload.get("records", [])
        return [r for r in (self._parse_row(row) for row in rows) if r is not None]

    def _parse_row(self, row: dict[str, Any]) -> Optional[PriceRecord]:
        raw_district = row.get("district")
        raw_commodity = row.get("commodity")
        raw_market = row.get("market")

        district = normalize_district(raw_district)
        commodity = normalize_commodity(raw_commodity)
        apmc = normalize_apmc(raw_market)

        if district not in TARGET_DISTRICTS:
            return None
        if not commodity or not apmc:
            # Skip exotic commodities we don't have an alias for — logged for review
            logger.debug("agmarknet: dropped row (unmapped) commodity=%r market=%r", raw_commodity, raw_market)
            return None

        try:
            arrival = date.fromisoformat(_iso_date(row.get("arrival_date")))
        except (ValueError, TypeError):
            return None

        return PriceRecord(
            trade_date=arrival,
            district=district,
            apmc=apmc,
            mandi_display=str(raw_market or apmc),
            commodity=commodity,
            variety=row.get("variety") or None,
            min_price=_to_decimal(row.get("min_price")),
            max_price=_to_decimal(row.get("max_price")),
            modal_price=_to_decimal(row.get("modal_price")),
            arrival_quantity_qtl=None,  # Agmarknet API does not expose arrivals on this endpoint
            source=self.name,
            raw=row,
        )


def _iso_date(ddmmyyyy: Any) -> str:
    """Convert '17/04/2026' → '2026-04-17'."""
    if not ddmmyyyy:
        return ""
    parts = str(ddmmyyyy).split("/")
    if len(parts) != 3:
        return str(ddmmyyyy)
    dd, mm, yyyy = parts
    return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
