"""AI-powered parsers for onboarding inputs.

Uses OpenRouter LLM to extract structured data from free-form farmer text.
Falls back to simple heuristics when the API key is absent or calls fail.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

_OR_URL = "https://openrouter.ai/api/v1/chat/completions"
_MODEL = "meta-llama/llama-3.1-8b-instruct"
_FALLBACK_MODEL = "google/gemma-2-9b-it:free"
_JSON_RE = re.compile(r"\{.*?\}", re.DOTALL)

_LOCATION_SYSTEM = """\
You are a location extractor for Kisan AI, a WhatsApp bot for Maharashtra farmers.
The farmer was asked: "Type your village, taluka and district."
They may write in Marathi (Devanagari), English, Hinglish, or any format/order.

Examples:
  "Vadegaon, Parner, Ahilyanagar" → {"village":"Vadegaon","taluka":"Parner","district":"Ahilyanagar"}
  "वडेगाव पारनेर अहिल्यानगर"     → {"village":"वडेगाव","taluka":"Parner","district":"Ahilyanagar"}
  "parner taluka ahmednagar"      → {"village":null,"taluka":"Parner","district":"Ahilyanagar"}
  "Kopargaon"                     → {"village":"Kopargaon","taluka":null,"district":null}

Return ONLY valid JSON with no markdown fences:
{"village":"<name or null>","taluka":"<name or null>","district":"<name or null>"}
"""

_CROPS_SYSTEM = """\
You are a crop extractor for Kisan AI, a WhatsApp bot for Maharashtra farmers.
The farmer was asked which crops they grow.
They may write in Marathi, English, or mixed.

Map what they say to slugs from this list ONLY:
  onion, tur, soyabean, cotton, tomato, potato, wheat, chana, jowar, bajra,
  pomegranate, grapes, maize

Marathi → slug:
  कांदा→onion  तूर→tur  सोयाबीन→soyabean  कापूस→cotton  टोमॅटो→tomato
  बटाटा→potato  गहू→wheat  हरभरा→chana  ज्वारी→jowar  बाजरी→bajra
  डाळिंब→pomegranate  द्राक्षे→grapes  मका→maize

Return ONLY valid JSON with no markdown fences:
{"crops":["<slug>","..."]}
Return {"crops":[]} if nothing is recognised.
"""


async def _llm_call(system: str, user_msg: str) -> Optional[str]:
    """Try primary then fallback model. Returns raw content or None."""
    api_key = settings.openrouter_api_key
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://kisan-ai-production-6f73.up.railway.app",
        "X-Title": "Kisan AI",
    }
    payload_base = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.0,
        "max_tokens": 120,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        for model in (_MODEL, _FALLBACK_MODEL):
            try:
                resp = await client.post(
                    _OR_URL,
                    headers=headers,
                    json={**payload_base, "model": model},
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as exc:
                logger.warning("ai_parser: model=%s failed: %s", model, exc)
    return None


def _parse_json(raw: str) -> Optional[dict]:
    m = _JSON_RE.search(raw)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


def _naive_location(text: str) -> dict:
    """Comma-split fallback when LLM is unavailable.

    Expects 'village, taluka, district' format as we ask the farmer to type.
    """
    parts = [p.strip() for p in re.split(r"[,،]", text) if p.strip()]
    return {
        "village": parts[0] if len(parts) > 0 else None,
        "taluka": parts[1] if len(parts) > 1 else None,
        "district": parts[2] if len(parts) > 2 else None,
    }


async def parse_location(text: str) -> dict:
    """Extract village, taluka, district from free text.

    Returns dict with keys 'village', 'taluka', 'district'.
    Any value may be None. Falls back to comma-split heuristic.
    """
    raw = await _llm_call(_LOCATION_SYSTEM, f'Farmer message: "{text}"')
    if raw:
        data = _parse_json(raw)
        if data:
            return {
                "village": data.get("village") or None,
                "taluka": data.get("taluka") or None,
                "district": data.get("district") or None,
            }
    return _naive_location(text)


async def parse_crops(text: str) -> list[str]:
    """Extract crop slugs from free text. Falls back to normalize_commodity."""
    raw = await _llm_call(_CROPS_SYSTEM, f'Farmer message: "{text}"')
    if raw:
        data = _parse_json(raw)
        if data:
            crops = [c for c in data.get("crops", []) if isinstance(c, str)]
            if crops:
                return crops

    # Fallback: token-by-token normalizer
    from src.ingestion.normalizer import normalize_commodity
    tokens = [t.strip() for t in re.split(r"[,\s]+", text) if t.strip()]
    return [c for c in (normalize_commodity(t) for t in tokens) if c]
