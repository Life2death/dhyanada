"""Tests for the merger — picks one winner per (date, apmc, commodity, variety)
using source preference rules.
"""
from datetime import date
from decimal import Decimal

from src.ingestion.merger import pick_winners
from src.ingestion.sources.base import PriceRecord


def _rec(source: str, commodity: str = "tur", apmc: str = "pune_market_yard", modal: str = "7500", variety=None) -> PriceRecord:
    return PriceRecord(
        trade_date=date(2026, 4, 17),
        district="pune",
        apmc=apmc,
        mandi_display=apmc.replace("_", " ").title(),
        commodity=commodity,
        variety=variety,
        modal_price=Decimal(modal),
        source=source,
    )


class TestMerger:
    def test_single_source_passes_through(self):
        records = [_rec("agmarknet")]
        winners = pick_winners(records)
        assert len(winners) == 1
        assert winners[0].source == "agmarknet"

    def test_default_priority_msamb_beats_agmarknet(self):
        records = [_rec("agmarknet", modal="7500"), _rec("msamb", modal="7600")]
        winners = pick_winners(records)
        assert len(winners) == 1
        assert winners[0].source == "msamb"
        assert winners[0].modal_price == Decimal("7600")

    def test_onion_nhrdf_wins(self):
        records = [
            _rec("msamb", commodity="onion", apmc="lasalgaon", modal="2100"),
            _rec("agmarknet", commodity="onion", apmc="lasalgaon", modal="2150"),
            _rec("nhrdf", commodity="onion", apmc="lasalgaon", modal="2080"),
        ]
        winners = pick_winners(records)
        assert len(winners) == 1
        assert winners[0].source == "nhrdf"

    def test_vashi_yard_prefers_vashi_source(self):
        records = [
            _rec("agmarknet", commodity="tur", apmc="vashi", modal="7400"),
            _rec("vashi", commodity="tur", apmc="vashi", modal="7520"),
            _rec("msamb", commodity="tur", apmc="vashi", modal="7480"),
        ]
        winners = pick_winners(records)
        assert len(winners) == 1
        assert winners[0].source == "vashi"

    def test_different_cells_both_kept(self):
        records = [
            _rec("msamb", commodity="tur", apmc="pune_market_yard"),
            _rec("msamb", commodity="onion", apmc="lasalgaon"),
        ]
        winners = pick_winners(records)
        assert len(winners) == 2

    def test_different_varieties_stay_separate(self):
        records = [
            _rec("msamb", commodity="cotton", variety="Local"),
            _rec("msamb", commodity="cotton", variety="Medium Staple"),
        ]
        winners = pick_winners(records)
        assert len(winners) == 2

    def test_drops_records_without_apmc(self):
        bad = PriceRecord(
            trade_date=date(2026, 4, 17),
            district="pune",
            apmc="",
            mandi_display="",
            commodity="tur",
            source="agmarknet",
        )
        good = _rec("agmarknet")
        winners = pick_winners([bad, good])
        assert len(winners) == 1
        assert winners[0].apmc == "pune_market_yard"

    def test_empty_input(self):
        assert pick_winners([]) == []
