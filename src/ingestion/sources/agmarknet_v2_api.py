"""Agmarknet v1 API scraper — the live price backbone.

Endpoint: POST https://api.agmarknet.gov.in/v1/daily-price-arrival/report
Auth:      None — completely public, no API key required.
Format:    JSON. Real-time Maharashtra prices for target commodities.

One POST per target commodity (12 crops). The API accepts all params as
strings; array filters use stringified JSON (e.g. '[20]' for Maharashtra).

Sentinel values:
  '[100001]'  All Districts
  '[100002]'  All Markets
  '[100003]'  All Grades
  '[100007]'  All Varieties

Response structure:
  data.records[0].data[]  — list of price rows
  data.records[0].pagination[0].total_pages — for pagination
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.ingestion.normalizer import normalize_apmc, normalize_district
from src.ingestion.sources.base import PriceRecord, PriceSource

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.agmarknet.gov.in/v1/daily-price-arrival/report"
_TIMEOUT = 30.0
_PAGE_SIZE = 100  # rows per page
_MAX_PAGES = 10   # safety cap per commodity

# Maharashtra state code in Agmarknet
_MH_STATE = "[20]"

# Sentinel values for "All X"
_ALL_DISTRICTS = "[100001]"
_ALL_MARKETS   = "[100002]"
_ALL_GRADES    = "[100003]"
_ALL_VARIETIES = "[100007]"

# Price data type
_DATA_TYPE_PRICE = "100004"

# Target commodities: canonical_slug → (group_id, commodity_id)
_COMMODITIES: dict[str, tuple[str, str]] = {
    "onion":       ("6", "23"),
    "tomato":      ("6", "65"),
    "potato":      ("6", "24"),
    "garlic":      ("6", "25"),
    "pomegranate": ("5", "160"),
    "grapes":      ("5", "22"),
    "soyabean":    ("3", "13"),
    "tur":         ("2", "45"),
    "gram":        ("2", "6"),
    "wheat":       ("1", "1"),
    "maize":       ("1", "4"),
    "jowar":       ("1", "5"),
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://agmarknet.gov.in/",
    "Origin": "https://agmarknet.gov.in",
    "Accept": "*/*",
    "Content-Type": "application/json",
}

_COMMA_RE = re.compile(r",")


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, "", "NA", "N/A", "-", "0", "0.00"):
        return None
    try:
        # Prices come as "8,000.00" — strip commas before parsing
        cleaned = _COMMA_RE.sub("", str(value)).strip()
        d = Decimal(cleaned)
        return d if d > 0 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def _parse_date(raw: Any) -> Optional[date]:
    """Parse 'DD-MM-YYYY' or 'YYYY-MM-DD' → date."""
    if not raw:
        return None
    s = str(raw).strip()
    # DD-MM-YYYY
    if len(s) == 10 and s[2] == "-" and s[5] == "-":
        try:
            return date(int(s[6:]), int(s[3:5]), int(s[:2]))
        except ValueError:
            pass
    # YYYY-MM-DD
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


class AgmarknetV2Source(PriceSource):
    """Scrapes live Maharashtra mandi prices from api.agmarknet.gov.in/v1/."""

    name = "agmarknet_v2"

    def __init__(self, timeout_s: float = _TIMEOUT, concurrency: int = 4):
        self._timeout = timeout_s
        self._sem = asyncio.Semaphore(concurrency)

    async def fetch(self, trade_date: date) -> list[PriceRecord]:
        async with httpx.AsyncClient(
            timeout=self._timeout, headers=_HEADERS, follow_redirects=True
        ) as client:
            tasks = [
                self._fetch_commodity(client, trade_date, slug, group_id, cmdt_id)
                for slug, (group_id, cmdt_id) in _COMMODITIES.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        records: list[PriceRecord] = []
        for slug, result in zip(_COMMODITIES.keys(), results):
            if isinstance(result, Exception):
                logger.warning("agmarknet_v2: %s failed: %s", slug, result)
            else:
                records.extend(result)

        logger.info("agmarknet_v2: fetched %d records for %s", len(records), trade_date)
        return records

    async def _fetch_commodity(
        self,
        client: httpx.AsyncClient,
        trade_date: date,
        slug: str,
        group_id: str,
        cmdt_id: str,
    ) -> list[PriceRecord]:
        async with self._sem:
            return await self._fetch_all_pages(client, trade_date, slug, group_id, cmdt_id)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def _fetch_all_pages(
        self,
        client: httpx.AsyncClient,
        trade_date: date,
        slug: str,
        group_id: str,
        cmdt_id: str,
    ) -> list[PriceRecord]:
        date_str = trade_date.strftime("%Y-%m-%d")
        records: list[PriceRecord] = []

        for page in range(1, _MAX_PAGES + 1):
            body = {
                "from_date": date_str,
                "to_date": date_str,
                "data_type": _DATA_TYPE_PRICE,
                "group": group_id,
                "commodity": cmdt_id,
                "state": _MH_STATE,
                "district": _ALL_DISTRICTS,
                "market": _ALL_MARKETS,
                "grade": _ALL_GRADES,
                "variety": _ALL_VARIETIES,
                "page": str(page),
                "limit": str(_PAGE_SIZE),
            }
            resp = await client.post(_BASE_URL, json=body)
            # 404 = no data for this commodity/date — not a real error
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            payload = resp.json()

            if not payload.get("status"):
                logger.debug("agmarknet_v2: %s page %d status=false", slug, page)
                break

            outer_records = payload.get("data", {}).get("records", [])
            if not outer_records:
                break

            # Each element in records[] has a .data[] sub-list of actual rows
            rows: list[dict] = []
            for block in outer_records:
                rows.extend(block.get("data", []))

            for row in rows:
                pr = self._parse_row(row, trade_date, slug)
                if pr is not None:
                    records.append(pr)

            # Pagination — check if more pages exist
            pagination = outer_records[0].get("pagination", [{}])
            total_pages = int(pagination[0].get("total_pages", 1)) if pagination else 1
            if page >= total_pages:
                break

        logger.debug("agmarknet_v2: %s → %d records", slug, len(records))
        return records

    def _parse_row(self, row: dict[str, Any], trade_date: date, slug: str) -> Optional[PriceRecord]:
        raw_district = row.get("district_name")
        raw_market = row.get("market_name")
        raw_date = row.get("arrival_date")

        # The API is already filtered to Maharashtra (state=[20]); accept all districts.
        # Use canonical slug if known; fall back to snake_case of the raw name.
        district = normalize_district(raw_district)
        if district is None and raw_district:
            district = re.sub(r"[^a-z0-9]+", "_", raw_district.strip().lower()).strip("_")
        if not district:
            return None

        apmc = normalize_apmc(raw_market)
        if not apmc:
            return None

        arrival = _parse_date(raw_date) or trade_date

        modal = _to_decimal(row.get("model_price"))
        low   = _to_decimal(row.get("min_price"))
        high  = _to_decimal(row.get("max_price"))

        if modal is None and low is None and high is None:
            return None

        qty = _to_decimal(row.get("arrival_qty"))

        return PriceRecord(
            trade_date=arrival,
            district=district,
            apmc=apmc,
            mandi_display=str(raw_market or apmc),
            commodity=slug,
            variety=row.get("variety_name") or None,
            min_price=low,
            max_price=high,
            modal_price=modal,
            arrival_quantity_qtl=qty,
            source=self.name,
            raw=row,
        )
