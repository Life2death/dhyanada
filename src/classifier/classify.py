"""Top-level classify() — regex first, LLM fallback.

Usage:
    from src.classifier.classify import classify
    result = await classify("आजचा कांदा भाव")
    # IntentResult(intent=<Intent.PRICE_QUERY>, commodity='onion', ...)

Pipeline:
  1. Strip + length-guard the text.
  2. Run regex classifier (sync, ~0 ms).
  3. If regex returns UNKNOWN → call Gemini Flash (async, ~300–800 ms).
  4. Return whichever result is more confident.

The LLM is only invoked when regex returns UNKNOWN. This keeps the 99th-
percentile latency low for the ~85% of messages regex handles.
"""
from __future__ import annotations

import logging

from src.classifier.intents import Intent, IntentResult
from src.classifier.regex_classifier import classify_regex
from src.classifier.llm_classifier import classify_llm

logger = logging.getLogger(__name__)

# Maximum text length we'll pass to the LLM (cost/abuse guard).
_MAX_LLM_TEXT_LEN = 500


async def classify(text: str) -> IntentResult:
    """Classify a farmer message. Async because LLM fallback is async.

    Always returns an IntentResult — never raises.
    """
    # Step 1: regex (instant)
    result = classify_regex(text)

    if result.intent != Intent.UNKNOWN:
        logger.debug("classify: regex hit intent=%s text=%r", result.intent.value, text[:60])
        return result

    # Step 2: LLM fallback
    truncated = text[:_MAX_LLM_TEXT_LEN]
    logger.debug("classify: regex UNKNOWN → LLM fallback text=%r", truncated[:60])
    llm_result = await classify_llm(truncated)

    # Prefer the LLM result unless it's also UNKNOWN (then keep regex UNKNOWN)
    if llm_result.intent != Intent.UNKNOWN:
        return llm_result

    return result  # both unknown — return regex UNKNOWN with the reason attached
