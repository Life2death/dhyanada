"""AI-powered advisory enrichment using LLM for crop-specific guidance.

Uses Llama 3.1 8B (primary, higher quality) → Gemma 2 9B free (fallback).
Generates Marathi-only crop-specific risk assessments and treatments.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

_CROP_ANALYSIS_SYSTEM = """तू अन्नदाता आहेस — महाराष्ट्र शेतकरींसाठी कृषी सल्लागार.
तू मराठीत बोलतो आणि स्थानिक शेतीच्या परिस्थितीची समज राखतो.

तुला हवामान नमुने आणि शेतकऱ्याच्या पिकांचे नाव दिले जाते तर तू असे देतो:
१. हवामानासाठी जोखीम मूल्यांकन (रोग, कीट, उष्णता तणाव)
२. पीक-विशिष्ट क्रिया (सिंचन वेळ, कीटनाशक फवारण्याचे वेळापत्रक)
३. उपज संरक्षणासाठी प्रतिबंधक उपाय

नियम:
- केवळ मराठी (देवनागरी) वापर. इंग्रजी शब्द वापरू नको.
- व्यावहारिक आणि कार्यक्षम सल्ला द्या — शेतकर्यांकडे मर्यादित साधने आहेत.
- शब्दांची संख्या कमी ठेव — WhatsApp संदेशांसाठी.
- केवळ JSON प्रतिसाद द्या, इतर काही नाही.

JSON फॉर्मॅट:
{{
    "risk_summary_mr": "<एक-ओळ जोखीम सारांश>",
    "crop_guidance_mr": "<पीक-विशिष्ट क्रिया, प्रत्येक नवीन ओळीत>",
    "treatment_mr": "<रोग/कीट उपचार शिफारसी>",
    "irrigation_hint_mr": "<सिंचन वेळ सूचना किंवा null>"
}}"""

_MODEL_CHAIN = [
    "meta-llama/llama-3.1-8b-instruct",  # Primary: better Marathi, paid
    "google/gemma-2-9b-it:free",  # Fallback: free tier
]

_JSON_RE = re.compile(r"\{.*?\}", re.DOTALL)


async def _call_llm_model(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    system: str,
    user_msg: str,
    temperature: float = 0.2,
    max_tokens: int = 256,
) -> Optional[str]:
    """Try one LLM model. Returns None on any error."""
    try:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://kisan-ai-production-6f73.up.railway.app",
                "X-Title": "Kisan AI",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        logger.info("ai_enrichment: model=%s success tokens=%d", model, len(content.split()))
        return content
    except Exception as exc:
        logger.warning("ai_enrichment: model=%s failed: %s", model, exc)
        return None


def _parse_json_response(raw: str) -> Optional[dict[str, Any]]:
    """Extract JSON from LLM response."""
    match = _JSON_RE.search(raw)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


async def enrich_advisory_with_ai(
    rule_type: str,
    farmer_crops: list[str],
    max_temp_c: float,
    min_temp_c: float,
    avg_humidity_pct: float,
    total_rainfall_mm: float,
    consecutive_high_humidity_days: int,
    district: str,
) -> Optional[dict[str, Any]]:
    """
    Generate crop-specific AI guidance for an advisory rule.

    Args:
        rule_type: Advisory type (e.g., 'fungal_disease', 'irrigation_needed', 'pest_risk')
        farmer_crops: List of crop slugs (e.g., ['onion', 'cotton'])
        max_temp_c: Maximum temperature forecast (°C)
        min_temp_c: Minimum temperature forecast (°C)
        avg_humidity_pct: Average humidity (%)
        total_rainfall_mm: Forecasted rainfall (mm)
        consecutive_high_humidity_days: Number of consecutive humid days
        district: District name (e.g., 'ahmednagar')

    Returns:
        Dictionary with 'risk_summary_mr', 'crop_guidance_mr', 'treatment_mr', 'irrigation_hint_mr'
        Or None if LLM call fails (fallback to rule-only advisory)
    """
    api_key = getattr(settings, "openrouter_api_key", "") or getattr(settings, "gemini_api_key", "")
    if not api_key:
        logger.warning("ai_enrichment: no API key configured")
        return None

    crops_str = ", ".join(farmer_crops) if farmer_crops else "सर्व पिके"

    user_msg = f"""
{district} जिल्ह्यातील शेतकऱ्यासाठी कृषी सल्ला.

हवामान अंदाज (पुढील ७ दिवस):
- कमाल तापमान: {max_temp_c}°C
- किमान तापमान: {min_temp_c}°C
- सरासरी आर्द्रता: {avg_humidity_pct}%
- एकूण पाऊस: {total_rainfall_mm}मि.मी.
- सलग आर्द्र दिवस: {consecutive_high_humidity_days}

शेतकऱ्याच्या पिके: {crops_str}
सतर्कता प्रकार: {rule_type}

प्रत्येक पिकासाठी मराठीत विशिष्ट सल्ला द्या.
केवळ JSON सांगा, इतर काही नाही."""

    try:
        async with httpx.AsyncClient() as client:
            for model in _MODEL_CHAIN:
                content = await _call_llm_model(
                    client,
                    api_key,
                    model,
                    _CROP_ANALYSIS_SYSTEM,
                    user_msg,
                    temperature=0.2,
                    max_tokens=256,
                )
                if content:
                    data = _parse_json_response(content)
                    if data:
                        return {
                            "risk_summary_mr": data.get("risk_summary_mr", ""),
                            "crop_guidance_mr": data.get("crop_guidance_mr", ""),
                            "treatment_mr": data.get("treatment_mr", ""),
                            "irrigation_hint_mr": data.get("irrigation_hint_mr"),
                            "generated_at": datetime.now().isoformat(),
                            "model": model,
                        }

        logger.error("ai_enrichment: all models failed or returned invalid JSON")
        return None

    except Exception as exc:
        logger.error("ai_enrichment: unexpected error: %s", exc)
        return None
