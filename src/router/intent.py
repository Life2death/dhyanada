"""Intent classification: regex-first, LLM fallback."""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical entity maps
# ---------------------------------------------------------------------------

CROP_MAP: dict[str, str] = {
    r"सोयाबीन|soyabean|soybean|soybin": "soyabean",
    r"तूर|tur|toor|tuur": "tur",
    r"कापूस|cotton|kapus|kapas|kaapus": "cotton",
}

DISTRICT_MAP: dict[str, str] = {
    r"लातूर|latur|laatur|laatuur": "latur",
    r"नांदेड|nanded|nandad": "nanded",
    r"जालना|jalna|jalna": "jalna",
    r"अकोला|akola": "akola",
    r"यवतमाळ|yavatmal|yawatmal": "yavatmal",
}

# ---------------------------------------------------------------------------
# Regex rules (covers ~70%+ of messages)
# ---------------------------------------------------------------------------

INTENT_RULES: dict[str, list[str]] = {
    "price_query": [
        r"price|भाव|दर|rate|bhav|bhaav|dar",
        r"सोयाबीन|soyabean|soybean|soybin|तूर|tur|toor|tuur|कापूस|cotton|kapus|kapas|kaapus",
    ],
    "greeting": [r"^(hi|hello|नमस्कार|namaskar|हॅलो)$"],
    "help": [r"^(help|मदत|menu|मेनू)$"],
    "stop": [r"^(stop|थांबा|बंद|opt.?out)$"],
    "delete": [r"^(delete|delete my data|माझा डेटा हटवा|erase)"],
    "subscribe": [r"upgrade|subscribe|paid|premium|सदस्यता"],
}

_compiled: dict[str, list[re.Pattern]] = {
    intent: [re.compile(p, re.IGNORECASE) for p in patterns]
    for intent, patterns in INTENT_RULES.items()
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class IntentResult:
    intent: str
    crop: Optional[str] = None
    district: Optional[str] = None
    confidence: str = "regex"  # 'regex' | 'llm' | 'unknown'
    raw_entities: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def classify(message: str) -> IntentResult:
    """Classify a farmer message into an intent with optional entity extraction."""
    text = message.strip()

    # 1. Regex pass
    matched_intent = _regex_classify(text)
    if matched_intent:
        return IntentResult(
            intent=matched_intent,
            crop=_extract_entity(text, CROP_MAP),
            district=_extract_entity(text, DISTRICT_MAP),
            confidence="regex",
        )

    # 2. LLM fallback
    try:
        return await _llm_classify(text)
    except Exception as exc:
        logger.warning("LLM intent fallback failed: %s", exc)
        return IntentResult(intent="unknown", confidence="unknown")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _regex_classify(text: str) -> Optional[str]:
    """Return first matching intent or None.

    price_query: matches if both a price-word AND a crop are present, OR if only
    a crop name is sent (farmers commonly type just the crop to ask its price),
    OR if only a price-word is sent (e.g. "भाव" = "what's the price?").
    """
    for intent, patterns in _compiled.items():
        if intent == "price_query":
            price_pat, crop_pat = patterns
            price_match = price_pat.search(text)
            crop_match = crop_pat.search(text)
            if price_match or crop_match:
                return intent
        else:
            if any(p.search(text) for p in patterns):
                return intent
    return None


def _extract_entity(text: str, entity_map: dict[str, str]) -> Optional[str]:
    for pattern, canonical in entity_map.items():
        if re.search(pattern, text, re.IGNORECASE):
            return canonical
    return None


async def _llm_classify(text: str) -> IntentResult:
    """Call Gemini Flash to classify messages that regex couldn't handle."""
    prompt = (
        "You are an intent classifier for a Marathi/English farming chatbot.\n"
        "Classify this message into one of: price_query, greeting, help, stop, delete, subscribe, unknown.\n"
        "Also extract entities: crop (soyabean/tur/cotton) and district (latur/nanded/jalna/akola/yavatmal).\n"
        'Respond ONLY with JSON: {"intent": "...", "crop": "...", "district": "..."}\n'
        f'Message: "{text}"'
    )

    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            params={"key": settings.gemini_api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        resp.raise_for_status()
        content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(content.strip().strip("```json").strip("```"))

    return IntentResult(
        intent=data.get("intent", "unknown"),
        crop=data.get("crop") or None,
        district=data.get("district") or None,
        confidence="llm",
        raw_entities=data,
    )
