"""NHRDF (National Horticulture Research & Development Foundation) onion feed.

URL: https://nhrdf.org/en-us/DailyWiseMarketArrivals
Why: Authoritative onion modal prices for Lasalgaon, Pimpalgaon, Vashi. When a
farmer asks about kanda/onion — this is the number traders trust.

Scope: onion only. Covers Nashik district (Lasalgaon, Pimpalgaon, Niphad, Yeola)
and Navi Mumbai (Vashi). Other sources carry onion too, but NHRDF wins the
merger preference for commodity='onion'.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.ingestion.normalizer import (
    TARGET_DISTRICTS,
    normalize_apmc,
    normalize_district,
)
from src.ingestion.sources.base import PriceRecord, PriceSource

logger = logging.getLogger(__name__)

_REPORT_URL = "https://nhrdf.org/en-us/DailyWiseMarketArrivals"
_UA = "Dhanyada/0.1 (+https://github.com/Life2death/dhanyada)"

# NHRDF market name → (district_display, district_canonical)
_MARKET_TO_DISTRICT: dict[str, str] = {
    "lasalgaon": "nashik",
    "pimpalgaon": "nashik",
    "niphad": "nashik",
    "yeola": "nashik",
    "manmad": "nashik",
    "nashik": "nashik",
    "vashi": "navi_mumbai",
    "mumbai": "navi_mumbai",
}


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, "", "-", "NA"):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


class NhrdfOnionSource(PriceSource):
    name = "nhrdf"

    def __init__(self, timeout_s: float = 30.0):
        self._timeout = timeout_s

    async def fetch(self, trade_date: date) -> list[PriceRecord]:
        headers = {"User-Agent": _UA}
        try:
            async with httpx.AsyncClient(timeout=self._timeout, headers=headers, follow_redirects=True) as client:
                html = await self._fetch_html(client, trade_date)
        except httpx.HTTPError as exc:
            logger.error("nhrdf: fetch failure: %s", exc)
            return []

        records = self._parse(html, trade_date)
        logger.info("nhrdf: fetched %d onion records for %s", len(records), trade_date)
        return records

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _fetch_html(self, client: httpx.AsyncClient, trade_date: date) -> str:
        # NHRDF exposes a date-parameterized GET. Exact param names are subject to change —
        # we use the public report URL with common query params seen in their form.
        params = {
            "DateFrom": trade_date.strftime("%d-%b-%Y"),
            "DateTo": trade_date.strftime("%d-%b-%Y"),
            "Commodity": "Onion",
        }
        resp = await client.get(_REPORT_URL, params=params)
        resp.raise_for_status()
        return resp.text

    def _parse(self, html: str, trade_date: date) -> list[PriceRecord]:
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table")
        if table is None:
            return []

        rows = table.find_all("tr")
        if len(rows) < 2:
            return []

        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
        out: list[PriceRecord] = []
        for tr in rows[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) < len(headers):
                continue
            row = dict(zip(headers, cells))

            market_raw = (row.get("market") or row.get("centre") or "").strip()
            if not market_raw:
                continue
            market_key = market_raw.lower().split()[0]
            district = _MARKET_TO_DISTRICT.get(market_key)
            if district not in TARGET_DISTRICTS:
                continue

            apmc = normalize_apmc(market_raw) or market_key
            out.append(
                PriceRecord(
                    trade_date=trade_date,
                    district=district,
                    apmc=apmc,
                    mandi_display=market_raw,
                    commodity="onion",
                    variety=row.get("variety") or None,
                    min_price=_to_decimal(row.get("min") or row.get("min price")),
                    max_price=_to_decimal(row.get("max") or row.get("max price")),
                    modal_price=_to_decimal(row.get("modal") or row.get("modal price")),
                    arrival_quantity_qtl=_to_decimal(row.get("arrival") or row.get("arrivals")),
                    source=self.name,
                    raw=row,
                )
            )
        return out
