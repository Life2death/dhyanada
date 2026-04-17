"""Normalize government scheme data across sources."""
import logging

logger = logging.getLogger(__name__)


# Scheme name aliases (Marathi, Hindi, English)
SCHEME_ALIASES = {
    # PM-KISAN
    "pm kisan": "pm_kisan",
    "pm kisan yojana": "pm_kisan",
    "kisan samman": "pm_kisan",
    "किसान सम्मान": "pm_kisan",
    "pm किसान": "pm_kisan",
    "prachaardhantri kisan": "pm_kisan",

    # PM-FASAL
    "pm fasal": "pm_fasal",
    "pm fasal bima": "pm_fasal",
    "fasal bima yojana": "pm_fasal",
    "प्रधानमंत्री फसल": "pm_fasal",
    "पीएम फसल": "pm_fasal",

    # Soil Health
    "soil health": "soil_health_card",
    "soil health card": "soil_health_card",
    "मिट्टी स्वास्थ्य": "soil_health_card",

    # Organic farming
    "organic farming": "pkvy_organic",
    "paramparagat krishi": "pkvy_organic",
    "परंपरागत कृषि": "pkvy_organic",
    "जैव खेती": "pkvy_organic",

    # Rashtriya Kranti
    "rashtriya kranti": "rashtriya_kranti_soil",
    "rashtriya kranti soil": "rashtriya_kranti_soil",
    "राष्ट्रीय क्रांति": "rashtriya_kranti_soil",
}

# Commodity aliases (Marathi, Hindi, English, transliteration)
COMMODITY_ALIASES = {
    # Wheat
    "wheat": "wheat",
    "गहू": "wheat",
    "gehun": "wheat",
    "गेहूं": "wheat",

    # Rice
    "rice": "rice",
    "चावल": "rice",
    "chawal": "rice",

    # Onion
    "onion": "onion",
    "कांदा": "onion",
    "kanda": "onion",
    "प्याज": "onion",

    # Cotton
    "cotton": "cotton",
    "कपास": "cotton",
    "kapas": "cotton",

    # Maize
    "maize": "maize",
    "मक्का": "maize",
    "makka": "maize",
    "corn": "maize",

    # Vegetables
    "vegetables": "vegetables",
    "सब्जियां": "vegetables",
    "sabzi": "vegetables",

    # Pulses
    "pulses": "pulses",
    "दाल": "pulses",
    "dal": "pulses",
    "दालें": "pulses",

    # Sugarcane
    "sugarcane": "sugarcane",
    "गन्ना": "sugarcane",
    "ganna": "sugarcane",

    # Potato
    "potato": "potato",
    "आलू": "potato",
    "alu": "potato",

    # Spices
    "spices": "spices",
    "मसाले": "spices",
    "masale": "spices",

    # All
    "all": "all",
    "सब": "all",
    "सभी": "all",
}

# District aliases
DISTRICT_ALIASES = {
    "pune": "pune",
    "पुणे": "pune",
    "pune": "pune",

    "ahmednagar": "ahilyanagar",
    "अहमदनगर": "ahilyanagar",
    "ahilyanagar": "ahilyanagar",
    "अहिल्यानगर": "ahilyanagar",

    "nashik": "nashik",
    "नाशिक": "nashik",

    "mumbai": "mumbai",
    "मुंबई": "mumbai",

    "navi mumbai": "navi_mumbai",
    "नवी मुंबई": "navi_mumbai",
    "thane": "navi_mumbai",  # Close to Navi Mumbai
    "ठाणे": "navi_mumbai",
}


def normalize_scheme_name(raw_name: str) -> str:
    """Normalize scheme name to canonical slug."""
    if not raw_name:
        return None

    cleaned = raw_name.lower().strip()
    return SCHEME_ALIASES.get(cleaned, raw_name)


def normalize_commodity(raw_name: str) -> str:
    """Normalize commodity name to canonical slug."""
    if not raw_name:
        return None

    cleaned = raw_name.lower().strip()
    return COMMODITY_ALIASES.get(cleaned, raw_name)


def normalize_district(raw_name: str) -> str:
    """Normalize district name to canonical slug."""
    if not raw_name:
        return None

    cleaned = raw_name.lower().strip()
    return DISTRICT_ALIASES.get(cleaned, raw_name)


def normalize_commodities_list(commodities: list[str]) -> list[str]:
    """Normalize list of commodity names."""
    if not commodities:
        return []

    normalized = []
    for commodity in commodities:
        normalized_name = normalize_commodity(commodity)
        if normalized_name and normalized_name != "all":
            normalized.append(normalized_name)

    return list(set(normalized))  # Remove duplicates
