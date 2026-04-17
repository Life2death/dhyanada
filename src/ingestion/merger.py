"""Merge records from multiple sources into one authoritative row per cell.

A "cell" is (trade_date, apmc, commodity, variety). Multiple sources may report
the same cell on the same day — the merger picks ONE winner per preference rules,
so the bot reads one clean number.

Preference rules (configurable):

  onion                → nhrdf > msamb > agmarknet > vashi
  everything at vashi  → vashi > msamb > agmarknet > nhrdf
  everything else      → msamb > agmarknet > vashi > nhrdf

Rationale:
- NHRDF is the authoritative onion quote traders use.
- Vashi's own feed beats Agmarknet for Vashi's own yard (Agmarknet undersamples).
- MSAMB is MH's marketing board — deepest APMC coverage, wins by default.
- Agmarknet is the federal fallback, wins when MSAMB misses a yard.

The merger never drops a record — it only picks a winner per cell. All source
records are still persisted (raw, per-source rows) so we can audit disagreements
and rebuild the winner view if we change preference rules later.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from src.ingestion.sources.base import PriceRecord


# Lower index = higher priority.
_DEFAULT_ORDER = ("msamb", "agmarknet", "vashi", "nhrdf")
_ONION_ORDER = ("nhrdf", "msamb", "agmarknet", "vashi")
_VASHI_ORDER = ("vashi", "msamb", "agmarknet", "nhrdf")


def _priority(source: str, ordering: tuple[str, ...]) -> int:
    try:
        return ordering.index(source)
    except ValueError:
        return len(ordering)  # unknown sources rank last


def _order_for(record: PriceRecord) -> tuple[str, ...]:
    if record.commodity == "onion":
        return _ONION_ORDER
    if record.apmc == "vashi":
        return _VASHI_ORDER
    return _DEFAULT_ORDER


def pick_winners(records: Iterable[PriceRecord]) -> list[PriceRecord]:
    """Return one record per (date, apmc, commodity, variety) cell.

    Records without a commodity or apmc are silently dropped — defensive;
    upstream parsers should not emit these but we don't want a single bad row
    to poison the batch.
    """
    buckets: dict[tuple, list[PriceRecord]] = defaultdict(list)
    for r in records:
        if not r.apmc or not r.commodity:
            continue
        key = (r.trade_date, r.apmc, r.commodity, r.variety)
        buckets[key].append(r)

    winners: list[PriceRecord] = []
    for cell_records in buckets.values():
        order = _order_for(cell_records[0])
        winner = min(cell_records, key=lambda rec: _priority(rec.source, order))
        winners.append(winner)
    return winners
