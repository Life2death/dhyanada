"""Vashi APMC direct scraper (Navi Mumbai wholesale).

Vashi is India's largest wholesale agri market, but Agmarknet frequently
underreports it (coverage gaps on ~30% of days). This source pulls directly
from the APMC's public arrival/price report page.

Reference URLs attempted in order:
  1. https://www.mahaapmc.com/ (Mahaapmc aggregator — has Vashi data)
  2. http://apmc.in/     (individual APMC listings)

Commodities: onion, potato, pulses (tur/chana), grains (wheat), tomato, grapes.

If both upstream sources are unreachable, returns [] — the orchestrator continues
with MSAMB/Agmarknet. This source is intentionally conservative: we'd rather
return nothing than bad data.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.ingestion.normalizer import normalize_commodity
from src.ingestion.sources.base import PriceRecord, PriceSource

logger = logging.getLogger(__name__)

_UPSTREAM_URLS = (
    "https://www.mahaapmc.com/Report/DailyReport",
    "http://apmc.in/Report/Vashi",
)
_UA = "Dhanyada/0.1 (+https://github.com/Life2death/dhanyada)"


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, "", "-", "NA"):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


class VashiApmcSource(PriceSource):
    name = "vashi"

    def __init__(self, timeout_s: float = 30.0):
        self._timeout = timeout_s

    async def fetch(self, trade_date: date) -> list[PriceRecord]:
        headers = {"User-Agent": _UA}
        async with httpx.AsyncClient(timeout=self._timeout, headers=headers, follow_redirects=True) as client:
            html: Optional[str] = None
            for url in _UPSTREAM_URLS:
                try:
                    html = await self._fetch_one(client, url, trade_date)
                    if html:
                        break
                except httpx.HTTPError as exc:
                    logger.warning("vashi: %s failed: %s", url, exc)
                    continue
            if not html:
                logger.error("vashi: all upstream URLs failed for %s", trade_date)
                return []

        records = self._parse(html, trade_date)
        logger.info("vashi: fetched %d records for %s", len(records), trade_date)
        return records

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=6),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _fetch_one(self, client: httpx.AsyncClient, url: str, trade_date: date) -> Optional[str]:
        params = {"date": trade_date.strftime("%d/%m/%Y"), "market": "Vashi"}
        resp = await client.get(url, params=params)
        if resp.status_code == 404:
            return None
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

            commodity = normalize_commodity(row.get("commodity") or row.get("item"))
            if not commodity:
                continue

            out.append(
                PriceRecord(
                    trade_date=trade_date,
                    district="navi_mumbai",
                    apmc="vashi",
                    mandi_display=row.get("market") or "Vashi APMC",
                    commodity=commodity,
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
