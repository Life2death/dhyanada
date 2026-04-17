"""Tests for Module 5 — intent classifier.

Covers:
- Regex classifier: English, Marathi, Hinglish price queries, subscribe/unsub,
  help, greeting, commodity extraction, district extraction, commodity-only messages
- Top-level classify(): regex wins, LLM fallback mock, LLM unavailable fallback
- handle_message() integration: classified + non-text path
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.classifier.intents import Intent, IntentResult
from src.classifier.regex_classifier import classify_regex
from src.handlers.webhook import IncomingMessage, handle_message


# ══════════════════════════════════════════════════════════
#  Regex classifier — price queries
# ══════════════════════════════════════════════════════════

class TestRegexPriceQuery:
    def test_english_price(self):
        r = classify_regex("What is today's onion price?")
        assert r.intent == Intent.PRICE_QUERY
        assert r.commodity == "onion"
        assert r.confidence == 1.0

    def test_hindi_bhav(self):
        r = classify_regex("aaj soyabean ka bhav kya hai")
        assert r.intent == Intent.PRICE_QUERY
        assert r.commodity == "soyabean"

    def test_marathi_kanda_bhav(self):
        r = classify_regex("आजचा कांदा भाव काय आहे?")
        assert r.intent == Intent.PRICE_QUERY
        assert r.commodity == "onion"

    def test_marathi_tur_dar(self):
        r = classify_regex("तूर दर किती आहे?")
        assert r.intent == Intent.PRICE_QUERY
        assert r.commodity == "tur"

    def test_nashik_district_extracted(self):
        r = classify_regex("Nashik mandi soyabean rate")
        assert r.district == "nashik"
        assert r.commodity == "soyabean"

    def test_pune_district_extracted(self):
        r = classify_regex("pune bazar me onion ka bhav")
        assert r.district == "pune"
        assert r.commodity == "onion"

    def test_commodity_only_implicit_price(self):
        r = classify_regex("cotton")
        assert r.intent == Intent.PRICE_QUERY
        assert r.commodity == "cotton"
        assert r.confidence == pytest.approx(0.85)
        assert r.explanation == "commodity_only_implicit_price"

    def test_marathi_commodity_only(self):
        r = classify_regex("सोयाबीन")
        assert r.intent == Intent.PRICE_QUERY
        assert r.commodity == "soyabean"

    def test_grapes_nashik(self):
        r = classify_regex("nashik grapes rate today")
        assert r.commodity == "grapes"
        assert r.district == "nashik"

    def test_pomegranate(self):
        r = classify_regex("डाळिंब भाव")
        assert r.commodity == "pomegranate"

    def test_vashi_to_navi_mumbai_district(self):
        r = classify_regex("vashi mandi onion price")
        assert r.district == "navi_mumbai"


# ══════════════════════════════════════════════════════════
#  Regex — subscribe / unsubscribe
# ══════════════════════════════════════════════════════════

class TestRegexSubscribe:
    def test_english_subscribe(self):
        assert classify_regex("subscribe").intent == Intent.SUBSCRIBE

    def test_marathi_subscribe(self):
        assert classify_regex("दैनिक भाव पाठवा").intent == Intent.SUBSCRIBE

    def test_marathi_ho(self):
        assert classify_regex("हो").intent == Intent.SUBSCRIBE

    def test_english_stop(self):
        assert classify_regex("stop").intent == Intent.UNSUBSCRIBE

    def test_marathi_nako(self):
        assert classify_regex("नको").intent == Intent.UNSUBSCRIBE

    def test_unsubscribe_beats_subscribe(self):
        # "band karo" has "band" which should match unsubscribe not subscribe
        assert classify_regex("band karo").intent == Intent.UNSUBSCRIBE


# ══════════════════════════════════════════════════════════
#  Regex — help / greeting / feedback
# ══════════════════════════════════════════════════════════

class TestRegexOther:
    def test_help_english(self):
        assert classify_regex("help").intent == Intent.HELP

    def test_help_marathi(self):
        assert classify_regex("मदत").intent == Intent.HELP

    def test_greeting_namaste(self):
        assert classify_regex("namaste").intent == Intent.GREETING

    def test_greeting_marathi(self):
        assert classify_regex("नमस्ते").intent == Intent.GREETING

    def test_greeting_hi(self):
        assert classify_regex("hi").intent == Intent.GREETING

    def test_feedback_thanks(self):
        assert classify_regex("thank you").intent == Intent.FEEDBACK

    def test_feedback_marathi_dhanyawad(self):
        assert classify_regex("धन्यवाद").intent == Intent.FEEDBACK

    def test_empty_text(self):
        r = classify_regex("")
        assert r.intent == Intent.UNKNOWN
        assert r.confidence == 0.0

    def test_gibberish_unknown(self):
        r = classify_regex("xkcd asdf 1234")
        assert r.intent == Intent.UNKNOWN


# ══════════════════════════════════════════════════════════
#  Top-level classify() — LLM fallback path
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_classify_regex_wins_no_llm_call():
    """When regex succeeds, LLM must NOT be called."""
    from src.classifier.classify import classify
    with patch("src.classifier.classify.classify_llm", new_callable=AsyncMock) as mock_llm:
        result = await classify("आजचा कांदा भाव")
        mock_llm.assert_not_called()
    assert result.intent == Intent.PRICE_QUERY
    assert result.commodity == "onion"


@pytest.mark.asyncio
async def test_classify_llm_called_on_unknown():
    """Regex UNKNOWN triggers LLM fallback."""
    from src.classifier.classify import classify
    llm_result = IntentResult(
        intent=Intent.SUBSCRIBE, confidence=0.9, source="llm", raw_text="daily milne chahiye"
    )
    with patch("src.classifier.classify.classify_llm", new_callable=AsyncMock, return_value=llm_result) as mock_llm:
        result = await classify("daily milne chahiye")
        mock_llm.assert_called_once()
    assert result.intent == Intent.SUBSCRIBE
    assert result.source == "llm"


@pytest.mark.asyncio
async def test_classify_returns_unknown_when_both_fail():
    """If regex AND LLM both return UNKNOWN, final result is UNKNOWN."""
    from src.classifier.classify import classify
    unknown = IntentResult(intent=Intent.UNKNOWN, confidence=0.0, source="llm", raw_text="?")
    with patch("src.classifier.classify.classify_llm", new_callable=AsyncMock, return_value=unknown):
        result = await classify("qwerty xyzzy")
    assert result.intent == Intent.UNKNOWN


# ══════════════════════════════════════════════════════════
#  handle_message() integration
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_handle_text_message_classified():
    msg = IncomingMessage(
        from_phone="919876543210",
        message_id="msg001",
        message_type="text",
        text="आजचा कांदा भाव काय आहे?",
    )
    result = await handle_message(msg)
    assert result["status"] == "classified"
    assert result["intent"] == Intent.PRICE_QUERY.value
    assert result["commodity"] == "onion"


@pytest.mark.asyncio
async def test_handle_non_text_message():
    msg = IncomingMessage(
        from_phone="919876543210",
        message_id="msg002",
        message_type="image",
        text=None,
    )
    result = await handle_message(msg)
    assert result["status"] == "non_text"
    assert result["intent"] == Intent.UNKNOWN.value


@pytest.mark.asyncio
async def test_handle_marathi_subscribe():
    msg = IncomingMessage(
        from_phone="919876543210",
        message_id="msg003",
        message_type="text",
        text="दैनिक भाव पाठवा",
    )
    result = await handle_message(msg)
    assert result["intent"] == Intent.SUBSCRIBE.value


@pytest.mark.asyncio
async def test_handle_needs_commodity_flag():
    """'price' without commodity → needs_commodity=True."""
    msg = IncomingMessage(
        from_phone="919876543210",
        message_id="msg004",
        message_type="text",
        text="aaj ka bhav kya hai",  # no commodity
    )
    result = await handle_message(msg)
    assert result["intent"] == Intent.PRICE_QUERY.value
    assert result["needs_commodity"] is True
