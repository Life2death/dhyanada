"""Gemini Flash LLM fallback classifier.

Called only when regex returns UNKNOWN. Costs ~0.001 ₹ per query at Gemini
Flash pricing — fine for the ~15% of messages regex can't classify.

Prompt strategy:
- Few-shot with real farmer messages (English + Marathi) to keep the model
  grounded. No chain-of-thought — we want a structured JSON output fast.
- The model must return JSON only: {"intent": "...", "confidence": 0.0–1.0,
  "commodity": "...|null", "district": "...|null", "explanation": "..."}
- We parse the JSON; if malformed, we return UNKNOWN rather than crashing.
- Gemini 1.5 Flash chosen: cheapest, fast (<1s), sufficient for intent.

Marathi: The system prompt explicitly tells the model to handle Marathi,
Hindi, and Hinglish. The few-shot examples include Marathi text.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from src.classifier.intents import Intent, IntentResult
from src.config import settings

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an intent classifier for Kisan AI, a WhatsApp bot serving farmers in Maharashtra, India.

You must classify incoming farmer messages into exactly one of these intents:
- price_query    : farmer wants today's mandi price (भाव / दर / rate / price)
- subscribe      : farmer wants daily price broadcasts (daily update / सुरू कर / हो / yes)
- unsubscribe    : farmer wants to stop broadcasts (stop / बंद / नको)
- onboarding     : new farmer asking how to use the service
- help           : asking for list of commands or features
- greeting       : just saying hello/namaste with no clear intent
- feedback       : giving feedback, complaint, or thanks
- unknown        : cannot classify

Farmers message in Marathi (Devanagari), English, or Hinglish (Hindi written in Latin script).
Extract commodity (canonical slug) if mentioned: onion, tur, soyabean, cotton, tomato, potato, wheat, chana, jowar, bajra, grapes, pomegranate, maize — or null.
Extract district (canonical slug) if mentioned: pune, ahilyanagar, navi_mumbai, mumbai, nashik — or null.

Respond ONLY with valid JSON, no markdown:
{"intent":"<slug>","confidence":<0.0-1.0>,"commodity":"<slug or null>","district":"<slug or null>","explanation":"<one line>"}
"""

_FEW_SHOT_EXAMPLES = [
    ("आजचा कांदा भाव काय आहे?",
     '{"intent":"price_query","confidence":0.99,"commodity":"onion","district":null,"explanation":"Marathi: today\'s onion price"}'),
    ("Nashik mandi me soyabean ka bhav kya hai",
     '{"intent":"price_query","confidence":0.98,"commodity":"soyabean","district":"nashik","explanation":"Hinglish price query with district"}'),
    ("Mala daily bhav pathva",
     '{"intent":"subscribe","confidence":0.97,"commodity":null,"district":null,"explanation":"Marathi: send daily price"}'),
    ("Stop karo sab",
     '{"intent":"unsubscribe","confidence":0.96,"commodity":null,"district":null,"explanation":"Hinglish unsubscribe"}'),
    ("नमस्ते",
     '{"intent":"greeting","confidence":1.0,"commodity":null,"district":null,"explanation":"Marathi greeting"}'),
    ("Mera registration kaise karo",
     '{"intent":"onboarding","confidence":0.95,"commodity":null,"district":null,"explanation":"Hinglish registration request"}'),
]


def _build_prompt(text: str) -> str:
    few_shot_block = "\n".join(
        f'User: "{msg}"\nAssistant: {resp}' for msg, resp in _FEW_SHOT_EXAMPLES
    )
    return f"{few_shot_block}\nUser: \"{text}\"\nAssistant:"


# ── Gemini client ──────────────────────────────────────────────────────────

def _get_gemini_client():
    """Lazy import — google-generativeai is optional if key not configured."""
    import google.generativeai as genai  # type: ignore[import]
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=_SYSTEM_PROMPT,
        generation_config={
            "temperature": 0.1,   # near-deterministic
            "max_output_tokens": 128,
            "response_mime_type": "application/json",
        },
    )


# ── JSON parsing ───────────────────────────────────────────────────────────

_VALID_INTENTS = {i.value for i in Intent}
_JSON_SNIPPET_RE = re.compile(r"\{.*?\}", re.DOTALL)


def _parse_llm_response(raw: str, text: str) -> IntentResult:
    """Parse Gemini's JSON response. Returns UNKNOWN on any parse error."""
    match = _JSON_SNIPPET_RE.search(raw)
    if not match:
        logger.warning("llm_classifier: no JSON in response: %r", raw[:200])
        return _fallback(text, "no_json_in_response")

    try:
        data: dict[str, Any] = json.loads(match.group())
    except json.JSONDecodeError as exc:
        logger.warning("llm_classifier: JSON decode error: %s — raw: %r", exc, raw[:200])
        return _fallback(text, "json_decode_error")

    intent_str = str(data.get("intent", "unknown")).lower()
    if intent_str not in _VALID_INTENTS:
        intent_str = "unknown"

    return IntentResult(
        intent=Intent(intent_str),
        confidence=float(data.get("confidence", 0.5)),
        commodity=data.get("commodity") or None,
        district=data.get("district") or None,
        source="llm",
        raw_text=text,
        explanation=str(data.get("explanation", "")),
    )


def _fallback(text: str, reason: str) -> IntentResult:
    return IntentResult(
        intent=Intent.UNKNOWN,
        confidence=0.0,
        source="llm",
        raw_text=text,
        explanation=reason,
    )


# ── Public API ─────────────────────────────────────────────────────────────

async def classify_llm(text: str) -> IntentResult:
    """Classify `text` using Gemini 1.5 Flash.

    Returns UNKNOWN if the API key is not configured, or on any API error.
    Never raises — the caller should always get a result.
    """
    if not settings.gemini_api_key:
        logger.warning("llm_classifier: GEMINI_API_KEY not set, returning UNKNOWN")
        return _fallback(text, "no_api_key")

    try:
        model = _get_gemini_client()
        prompt = _build_prompt(text)
        response = model.generate_content(prompt)
        raw = response.text or ""
        result = _parse_llm_response(raw, text)
        logger.info(
            "llm_classifier: intent=%s confidence=%.2f commodity=%s text=%r",
            result.intent.value, result.confidence, result.commodity, text[:60],
        )
        return result
    except Exception as exc:  # noqa: BLE001
        logger.error("llm_classifier: API error: %s", exc)
        return _fallback(text, f"api_error:{type(exc).__name__}")
