"""Abstract base for price sources.

Every source (Agmarknet API, MSAMB scraper, NHRDF, Vashi) implements `fetch()`
returning a list of `PriceRecord`. The orchestrator runs them in parallel,
the merger dedupes across sources, the persister upserts into Postgres.

Why a dataclass instead of the SQLAlchemy model? Sources produce plain data;
we don't want scrapers holding ORM sessions or knowing about DB constraints.
The orchestrator is the only layer that converts `PriceRecord` → `MandiPrice`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional


@dataclass(slots=True)
class PriceRecord:
    """One price observation from one source, already canonicalized."""

    trade_date: date
    district: str                  # canonical slug — see normalizer.TARGET_DISTRICTS
    apmc: str                      # canonical APMC slug
    mandi_display: str             # original human-readable name (for UI)
    commodity: str                 # canonical commodity slug
    variety: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    modal_price: Optional[Decimal] = None
    arrival_quantity_qtl: Optional[Decimal] = None
    source: str = ""               # 'agmarknet' | 'msamb' | 'nhrdf' | 'vashi'
    raw: dict[str, Any] = field(default_factory=dict)

    def dedupe_key(self) -> tuple:
        """Key used by merger — matches the DB unique constraint."""
        return (self.trade_date, self.apmc, self.commodity, self.variety, self.source)


class PriceSource(ABC):
    """One external price feed. Stateless — receives a date, returns records."""

    #: Short slug used in `PriceRecord.source` and preference rules.
    name: str = ""

    @abstractmethod
    async def fetch(self, trade_date: date) -> list[PriceRecord]:
        """Return all price observations for the given date (IST).

        Implementations should:
        - Swallow no exceptions — let the orchestrator decide retry/alert.
        - Filter to `normalizer.TARGET_DISTRICTS` where possible (server-side)
          but the orchestrator re-filters defensively.
        - Return [] if the source genuinely has no data (weekend, holiday).
        """
        raise NotImplementedError
