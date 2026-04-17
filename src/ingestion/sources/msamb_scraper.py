"""MSAMB (Maharashtra State Agricultural Marketing Board) scraper.

URL: https://www.msamb.com/ApmcDetail/ArrivalPriceReport
Why: Deeper APMC coverage for MH than Agmarknet (catches Udgir, Washim, smaller
yards). MSAMB is the state marketing board — most authoritative for MH.

Strategy:
- POST form with date + commodity filters, parse HTML table.
- Site uses ASP.NET viewstate; we fetch the page first to extract __VIEWSTATE
  and __EVENTVALIDATION, then submit the form.
- Be polite: 1 request per 2s, User-Agent identifies us.

This is the fragile source (HTML changes break parsing). When it fails, the
orchestrator logs and moves on — Agmarknet is the backbone fallback.
"""
from __future__ import annotations

import asyncio
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
    normalize_commodity,
    normalize_district,
)
from src.ingestion.sources.base import PriceRecord, PriceSource

logger = logging.getLogger(__name__)

_REPORT_URL = "https://www.msamb.com/ApmcDetail/ArrivalPriceReport"
_UA = "KisanAI/0.1 (+https://github.com/Life2death/kisan-ai) mandi-price-bot"
_POLITE_DELAY_S = 2.0


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s or s in ("-", "NA"):
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


class MsambScraperSource(PriceSource):
    name = "msamb"

    def __init__(self, timeout_s: float = 45.0):
        self._timeout = timeout_s

    async def fetch(self, trade_date: date) -> list[PriceRecord]:
        records: list[PriceRecord] = []
        headers = {"User-Agent": _UA, "Accept-Language": "en-IN,en;q=0.9,mr;q=0.8"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout, headers=headers, follow_redirects=True) as client:
                # One report pull per target district keeps payloads parseable.
                for district_display in ("Pune", "Ahmednagar", "Thane", "Mumbai", "Nashik"):
                    try:
                        html = await self._fetch_report(client, district_display, trade_date)
                        records.extend(self._parse_report(html, trade_date))
                    except Exception as exc:  # individual district failures should not kill the batch
                        logger.warning("msamb: district=%s failed: %s", district_display, exc)
                    await asyncio.sleep(_POLITE_DELAY_S)
        except httpx.HTTPError as exc:
            logger.error("msamb: connection failure: %s", exc)
            return []

        logger.info("msamb: fetched %d records for %s", len(records), trade_date)
        return records

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=6),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _fetch_report(
        self, client: httpx.AsyncClient, district_display: str, trade_date: date
    ) -> str:
        """GET the form page, extract viewstate tokens, POST the filter."""
        initial = await client.get(_REPORT_URL)
        initial.raise_for_status()
        soup = BeautifulSoup(initial.text, "lxml")

        form_data: dict[str, str] = {}
        for hidden in soup.select("input[type=hidden]"):
            name = hidden.get("name")
            if name:
                form_data[name] = hidden.get("value", "")

        # Known form field names on the MSAMB report page (subject to change).
        form_data.update(
            {
                "ctl00$ContentPlaceHolder1$txtDateFrom": trade_date.strftime("%d/%m/%Y"),
                "ctl00$ContentPlaceHolder1$txtDateTo": trade_date.strftime("%d/%m/%Y"),
                "ctl00$ContentPlaceHolder1$ddlDistrict": district_display,
                "ctl00$ContentPlaceHolder1$btnSearch": "Search",
            }
        )
        resp = await client.post(_REPORT_URL, data=form_data)
        resp.raise_for_status()
        return resp.text

    def _parse_report(self, html: str, trade_date: date) -> list[PriceRecord]:
        soup = BeautifulSoup(html, "lxml")
        # MSAMB wraps the results in a <table> with id containing "grdReport" or similar.
        table = soup.find("table", id=lambda v: bool(v) and ("Report" in v or "grd" in v))
        if table is None:
            return []

        rows = table.find_all("tr")
        if len(rows) < 2:
            return []

        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
        # Expected columns (subject to MSAMB layout): District, APMC, Commodity, Variety,
        # Arrivals, Min, Max, Modal. We look up indices defensively so a column reorder
        # doesn't break parsing.
        idx = {name: headers.index(name) for name in headers}

        out: list[PriceRecord] = []
        for tr in rows[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) < len(headers):
                continue
            row = {headers[i]: cells[i] for i in range(len(headers))}

            district = normalize_district(row.get("district"))
            if district not in TARGET_DISTRICTS:
                continue
            commodity = normalize_commodity(row.get("commodity"))
            apmc = normalize_apmc(row.get("apmc") or row.get("market"))
            if not commodity or not apmc:
                continue

            out.append(
                PriceRecord(
                    trade_date=trade_date,
                    district=district,
                    apmc=apmc,
                    mandi_display=row.get("apmc") or row.get("market") or apmc,
                    commodity=commodity,
                    variety=row.get("variety") or None,
                    min_price=_to_decimal(row.get("min") or row.get("min price")),
                    max_price=_to_decimal(row.get("max") or row.get("max price")),
                    modal_price=_to_decimal(row.get("modal") or row.get("modal price")),
                    arrival_quantity_qtl=_to_decimal(row.get("arrivals") or row.get("arrival")),
                    source=self.name,
                    raw=row,
                )
            )
        return out
