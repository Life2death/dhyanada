"""Tests for the normalizer — the layer that turns messy source data into
canonical slugs the merger can dedupe on.
"""
from src.ingestion.normalizer import (
    TARGET_DISTRICTS,
    normalize_apmc,
    normalize_commodity,
    normalize_district,
)


class TestDistrict:
    def test_ahmednagar_maps_to_ahilyanagar(self):
        assert normalize_district("Ahmednagar") == "ahilyanagar"
        assert normalize_district("AHMEDNAGAR") == "ahilyanagar"
        assert normalize_district("ahmadnagar") == "ahilyanagar"

    def test_devanagari_district(self):
        assert normalize_district("पुणे") == "pune"
        assert normalize_district("नाशिक") == "nashik"
        assert normalize_district("मुंबई") == "mumbai"

    def test_thane_routes_to_navi_mumbai(self):
        # Agmarknet files Vashi under Thane district — we remap.
        assert normalize_district("Thane") == "navi_mumbai"

    def test_unknown_district(self):
        assert normalize_district("Sangli") is None

    def test_all_targets_are_slugs(self):
        for slug in TARGET_DISTRICTS:
            assert slug.islower()
            assert " " not in slug


class TestCommodity:
    def test_tur_variants(self):
        assert normalize_commodity("Tur") == "tur"
        assert normalize_commodity("Arhar") == "tur"
        assert normalize_commodity("Red Gram") == "tur"
        assert normalize_commodity("तूर") == "tur"

    def test_onion_variants(self):
        assert normalize_commodity("Onion") == "onion"
        assert normalize_commodity("Onion(Red)") == "onion"
        assert normalize_commodity("Kanda") == "onion"
        assert normalize_commodity("कांदा") == "onion"

    def test_soyabean_spellings(self):
        for variant in ("Soyabean", "Soya Bean", "Soyabeen", "Soybean", "सोयाबीन"):
            assert normalize_commodity(variant) == "soyabean"

    def test_parenthetical_variety_stripped(self):
        # e.g. "Cotton(Medium Staple)" → cotton
        assert normalize_commodity("Cotton(Medium Staple)") == "cotton"

    def test_unknown_commodity(self):
        assert normalize_commodity("Quinoa") is None


class TestApmc:
    def test_vashi_variants(self):
        assert normalize_apmc("Vashi") == "vashi"
        assert normalize_apmc("Vashi APMC") == "vashi"
        assert normalize_apmc("Navi Mumbai") == "vashi"

    def test_lasalgaon_with_niphad(self):
        assert normalize_apmc("Lasalgaon(Niphad)") == "lasalgaon"

    def test_pune_market_yard(self):
        assert normalize_apmc("Pune") == "pune_market_yard"
        assert normalize_apmc("Market Yard") == "pune_market_yard"

    def test_unknown_apmc_falls_back_to_snake_case(self):
        # Unknown APMCs still get a stable dedupe key
        assert normalize_apmc("Some New Yard") == "some_new_yard"
