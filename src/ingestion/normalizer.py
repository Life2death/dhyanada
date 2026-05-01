"""Canonicalize messy strings from multiple price sources.

Sources disagree on spelling (Ahmednagar vs Ahilyanagar, Tur vs Arhar vs Red Gram),
mix languages (कांदा / Onion / Kanda), and vary in case / whitespace / punctuation.
The normalizer maps all variants to a single canonical slug so the merger can
dedupe reliably.

Canonical slugs are lowercase snake_case ASCII. Marathi aliases are included here
(not in Module 9) because ingestion data occasionally arrives in Devanagari and
farmers' queries will too — keeping one dictionary avoids drift.
"""
from __future__ import annotations

import re
from typing import Optional

# ---------- Districts ----------

_DISTRICT_ALIASES: dict[str, str] = {
    # Pune
    "pune": "pune",
    "पुणे": "pune",
    # Ahilyanagar (renamed from Ahmednagar in 2023 — both forms appear in data)
    "ahilyanagar": "ahilyanagar",
    "ahmednagar": "ahilyanagar",
    "ahmadnagar": "ahilyanagar",
    "a.nagar": "ahilyanagar",
    "a. nagar": "ahilyanagar",
    "अहिल्यानगर": "ahilyanagar",
    "अहमदनगर": "ahilyanagar",
    # Navi Mumbai
    "navi mumbai": "navi_mumbai",
    "navi-mumbai": "navi_mumbai",
    "new mumbai": "navi_mumbai",
    "thane": "navi_mumbai",  # Vashi APMC administratively sits under Thane in some feeds
    "नवी मुंबई": "navi_mumbai",
    # Mumbai
    "mumbai": "mumbai",
    "bombay": "mumbai",
    "मुंबई": "mumbai",
    # Nashik
    "nashik": "nashik",
    "nasik": "nashik",
    "नाशिक": "nashik",
    # Amravati (Vidarbha — cotton/soyabean belt)
    "amravati": "amravati",
    "amarawati": "amravati",
    "amrawati": "amravati",
    "अमरावती": "amravati",
    # Akola (cotton/soyabean)
    "akola": "akola",
    "अकोला": "akola",
    # Nagpur (orange/cotton)
    "nagpur": "nagpur",
    "नागपूर": "nagpur",
    # Latur (tur/soyabean, Marathwada)
    "latur": "latur",
    "लातूर": "latur",
    # Sangli (grapes/turmeric)
    "sangli": "sangli",
    "सांगली": "sangli",
    # Solapur (pomegranate/onion)
    "solapur": "solapur",
    "sholapur": "solapur",
    "सोलापूर": "solapur",
    # Kolhapur
    "kolhapur": "kolhapur",
    "कोल्हापूर": "kolhapur",
    # Satara
    "satara": "satara",
    "सातारा": "satara",
    # Jalgaon (banana/cotton)
    "jalgaon": "jalgaon",
    "जळगाव": "jalgaon",
    # Aurangabad / Chhatrapati Sambhajinagar
    "aurangabad": "aurangabad",
    "chhatrapati sambhajinagar": "aurangabad",
    "छत्रपती संभाजीनगर": "aurangabad",
    # Wardha (cotton)
    "wardha": "wardha",
    "वर्धा": "wardha",
    # Yavatmal (cotton)
    "yavatmal": "yavatmal",
    "यवतमाळ": "yavatmal",
    # Nanded (Marathwada)
    "nanded": "nanded",
    "नांदेड": "nanded",
    # Osmanabad / Dharashiv
    "osmanabad": "osmanabad",
    "dharashiv": "osmanabad",
}

# ---------- APMCs ----------

_APMC_ALIASES: dict[str, str] = {
    # Pune district
    "pune": "pune_market_yard",
    "pune (market yard)": "pune_market_yard",
    "pune(moshi)": "pune_moshi",
    "market yard": "pune_market_yard",
    "gultekdi": "pune_market_yard",
    "khed": "khed",
    "khed(chakan)": "khed",
    "manchar": "manchar",
    "baramati": "baramati",
    "indapur": "indapur",
    "junnar": "junnar",
    # Ahilyanagar district
    "ahmednagar": "ahmednagar_apmc",
    "ahilyanagar": "ahmednagar_apmc",
    "sangamner": "sangamner",
    "rahuri": "rahuri",
    "rahata": "rahata",
    "shrirampur": "shrirampur",
    "kopargaon": "kopargaon",
    "newasa": "newasa",
    # Navi Mumbai / Vashi
    "vashi": "vashi",
    "vashi new mumbai": "vashi",
    "vashi apmc": "vashi",
    "mumbai (navi mumbai)": "vashi",
    "navi mumbai": "vashi",
    # Mumbai (retail markets, limited APMC data)
    "mumbai": "mumbai_wholesale",
    "dana bazar": "mumbai_wholesale",
    # Nashik district
    "nashik": "nashik",
    "lasalgaon": "lasalgaon",
    "lasalgaon(niphad)": "lasalgaon",
    "pimpalgaon": "pimpalgaon",
    "pimpalgaon baswant": "pimpalgaon",
    "niphad": "niphad",
    "yeola": "yeola",
    "manmad": "manmad",
    "sinnar": "sinnar",
    "satana": "satana",
    "chandwad": "chandwad",
    "devla": "devla",
}

# ---------- Commodities ----------

_COMMODITY_ALIASES: dict[str, str] = {
    # Onion (flagship for Nashik/Lasalgaon)
    "onion": "onion",
    "onion(red)": "onion",
    "onion red": "onion",
    "onion(white)": "onion_white",
    "onion white": "onion_white",
    "kanda": "onion",
    "कांदा": "onion",
    "pyaaz": "onion",
    "pyaz": "onion",
    # Tur / Arhar / Red Gram — same crop, three names
    "tur": "tur",
    "toor": "tur",
    "arhar": "tur",
    "red gram": "tur",
    "red gram dal": "tur",
    "pigeon pea": "tur",
    "तूर": "tur",
    # Soyabean — multiple spellings
    "soyabean": "soyabean",
    "soya bean": "soyabean",
    "soyabeen": "soyabean",
    "soybean": "soyabean",
    "soyabin": "soyabean",
    "सोयाबीन": "soyabean",
    # Tomato
    "tomato": "tomato",
    "टोमॅटो": "tomato",
    "tamatar": "tomato",
    # Potato
    "potato": "potato",
    "aloo": "potato",
    "बटाटा": "potato",
    # Wheat
    "wheat": "wheat",
    "gehu": "wheat",
    "गहू": "wheat",
    # Gram / Chana
    "gram": "chana",
    "chana": "chana",
    "bengal gram": "chana",
    "चणा": "chana",
    "harbhara": "chana",
    # Jowar / Bajra / Maize
    "jowar": "jowar",
    "sorghum": "jowar",
    "ज्वारी": "jowar",
    "bajra": "bajra",
    "pearl millet": "bajra",
    "bajra(pearl millet/cumbu)": "bajra",
    "बाजरी": "bajra",
    "maize": "maize",
    "corn": "maize",
    "मका": "maize",
    # Sugarcane
    "sugarcane": "sugarcane",
    "ऊस": "sugarcane",
    # Grapes (Nashik speciality)
    "grapes": "grapes",
    "द्राक्षे": "grapes",
    # Pomegranate (Ahilyanagar/Nashik belt)
    "pomegranate": "pomegranate",
    "डाळिंब": "pomegranate",
    # Garlic (important in Pune/Nashik belt)
    "garlic": "garlic",
    "lahsun": "garlic",
    "lasun": "garlic",
    "लसूण": "garlic",
    # Cotton (Vidarbha belt — Akola, Amravati, Yavatmal)
    "cotton": "cotton",
    "cotton(unginned)": "cotton",
    "cotton(medium staple)": "cotton",
    "kapas": "cotton",
    "कापूस": "cotton",
    # Groundnut (oilseed, important in Nashik/Pune belt)
    "groundnut": "groundnut",
    "groundnut pods(raw)": "groundnut",
    "moongphali": "groundnut",
    "shengdana": "groundnut",
    "शेंगदाणा": "groundnut",
    # Turmeric (Sangli — India's largest turmeric market)
    "turmeric": "turmeric",
    "turmeric(raw)": "turmeric",
    "haldi": "turmeric",
    "हळद": "turmeric",
    # Green chilli
    "green chilli": "green_chilli",
    "green chilly": "green_chilli",
    "chilli": "chilli",
    "chilly": "chilli",
    "मिरची": "chilli",
    # Bengal gram variants
    "bengal gram(gram)(whole)": "chana",
    "gram(whole)": "chana",
    # Additional produce
    "bhindi(ladies finger)": "bhindi",
    "ladies finger": "bhindi",
    "bottle gourd": "bottle_gourd",
    "guar": "guar",
    "spinach": "spinach",
}

# ---------- Helpers ----------

_WHITESPACE_RE = re.compile(r"\s+")


def _clean(value: str) -> str:
    """Lower, strip, collapse internal whitespace, drop trailing punctuation."""
    v = value.strip().lower()
    v = _WHITESPACE_RE.sub(" ", v)
    v = v.strip(".,;:-_")
    return v


def normalize_district(raw: Optional[str]) -> Optional[str]:
    """Map any district spelling/language to canonical slug, or None if unknown."""
    if not raw:
        return None
    return _DISTRICT_ALIASES.get(_clean(raw))


def normalize_apmc(raw: Optional[str]) -> Optional[str]:
    """Map any APMC/mandi name to canonical slug. Falls back to snake_case of input."""
    if not raw:
        return None
    cleaned = _clean(raw)
    if cleaned in _APMC_ALIASES:
        return _APMC_ALIASES[cleaned]
    # Fallback: snake_case the input so we at least have a stable dedupe key
    return re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_") or None


def normalize_commodity(raw: Optional[str]) -> Optional[str]:
    """Map any commodity spelling/language to canonical slug, or None if unknown."""
    if not raw:
        return None
    cleaned = _clean(raw)
    if cleaned in _COMMODITY_ALIASES:
        return _COMMODITY_ALIASES[cleaned]
    # Try stripping parenthetical variety suffix: "Cotton(Medium Staple)" -> "cotton"
    stripped = re.sub(r"\(.*?\)", "", cleaned).strip()
    return _COMMODITY_ALIASES.get(stripped)


# Canonical district set used for filtering in the orchestrator.
TARGET_DISTRICTS = frozenset(
    {"pune", "ahilyanagar", "navi_mumbai", "mumbai", "nashik"}
)
