"""Tests for onboarding state machine — full Marathi flow with Redis mocked."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.handlers.onboarding import (
    OnboardingSession,
    handle,
    load_session,
    save_session,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_redis_mock(stored: dict | None = None):
    """Return a mock Redis async context manager with optional pre-loaded key."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=json.dumps(stored) if stored else None)
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=redis_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm, redis_mock


# ---------------------------------------------------------------------------
# New user → consent prompt
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_user_receives_consent_prompt_marathi():
    cm, _ = _make_redis_mock()
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+919876543210", "नमस्कार")
    assert "महाराष्ट्र किसान AI" in response
    assert "हो" in response


@pytest.mark.asyncio
async def test_new_user_english_hi_receives_bilingual_consent():
    cm, _ = _make_redis_mock()
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+919876543210", "hi")
    assert "Welcome to Maharashtra Kisan AI" in response
    assert "YES" in response


# ---------------------------------------------------------------------------
# Consent step
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consent_hao_in_marathi_advances_to_name():
    session_data = {"phone": "+91123", "state": "awaiting_consent",
                    "name": None, "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": False}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "हो")
    assert "नाव" in response or "name" in response.lower()


@pytest.mark.asyncio
async def test_consent_yes_english_advances_to_name():
    session_data = {"phone": "+91123", "state": "awaiting_consent",
                    "name": None, "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": False}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "YES")
    assert "नाव" in response or "name" in response.lower()


@pytest.mark.asyncio
async def test_consent_ha_alternate_accepted():
    session_data = {"phone": "+91123", "state": "awaiting_consent",
                    "name": None, "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": False}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "ha")
    assert "नाव" in response or "name" in response.lower()


@pytest.mark.asyncio
async def test_consent_nahi_in_marathi_opts_out():
    session_data = {"phone": "+91123", "state": "awaiting_consent",
                    "name": None, "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": False}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "नाही")
    assert "नाकारण्यात" in response or "declined" in response.lower() or "ठीक" in response


@pytest.mark.asyncio
async def test_consent_invalid_reply_prompts_retry():
    session_data = {"phone": "+91123", "state": "awaiting_consent",
                    "name": None, "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": False}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "कदाचित")
    assert "हो" in response or "YES" in response


# ---------------------------------------------------------------------------
# Name step
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_name_marathi_accepted():
    session_data = {"phone": "+91123", "state": "awaiting_name",
                    "name": None, "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "रामराव पाटील")
    assert "रामराव पाटील" in response or "जिल्हा" in response


@pytest.mark.asyncio
async def test_name_single_char_rejected():
    session_data = {"phone": "+91123", "state": "awaiting_name",
                    "name": None, "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "र")
    assert "नाव" in response or "name" in response.lower()


# ---------------------------------------------------------------------------
# District step
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_district_latur_marathi():
    session_data = {"phone": "+91123", "state": "awaiting_district",
                    "name": "रामराव", "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "लातूर")
    assert "पीक" in response or "crop" in response.lower()


@pytest.mark.asyncio
async def test_district_nanded_english():
    session_data = {"phone": "+91123", "state": "awaiting_district",
                    "name": "Ramrao", "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "nanded")
    assert "पीक" in response or "crop" in response.lower()


@pytest.mark.asyncio
async def test_district_akola_marathi():
    session_data = {"phone": "+91123", "state": "awaiting_district",
                    "name": "सुभाष", "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "अकोला")
    assert "पीक" in response or "crop" in response.lower()


@pytest.mark.asyncio
async def test_district_invalid_prompts_retry():
    session_data = {"phone": "+91123", "state": "awaiting_district",
                    "name": "Ravi", "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "पुणे")
    assert "Latur" in response or "ओळखता" in response


# ---------------------------------------------------------------------------
# Crops step
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crop_soyabean_marathi():
    session_data = {"phone": "+91123", "state": "awaiting_crops",
                    "name": "रामराव", "district": "latur", "crops": [],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "सोयाबीन")
    assert "भाषा" in response or "language" in response.lower()


@pytest.mark.asyncio
async def test_crop_tur_transliteration():
    session_data = {"phone": "+91123", "state": "awaiting_crops",
                    "name": "रामराव", "district": "nanded", "crops": [],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "tur")
    assert "भाषा" in response or "language" in response.lower()


@pytest.mark.asyncio
async def test_crop_multiple_comma_separated():
    session_data = {"phone": "+91123", "state": "awaiting_crops",
                    "name": "Suresh", "district": "akola", "crops": [],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "सोयाबीन, कापूस")
    assert "भाषा" in response or "language" in response.lower()


@pytest.mark.asyncio
async def test_crop_invalid_prompts_retry():
    session_data = {"phone": "+91123", "state": "awaiting_crops",
                    "name": "Ravi", "district": "latur", "crops": [],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "गहू")
    assert "Soyabean" in response or "ओळखता" in response


# ---------------------------------------------------------------------------
# Language step
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_language_1_marathi_completes_onboarding():
    session_data = {"phone": "+91123", "state": "awaiting_language",
                    "name": "रामराव", "district": "latur", "crops": ["soyabean"],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        with patch("src.handlers.onboarding._persist_to_db", new_callable=AsyncMock):
            response = await handle("+91123", "1")
    assert "नोंदणी पूर्ण" in response or "भाव" in response


@pytest.mark.asyncio
async def test_language_2_english_completes_onboarding():
    session_data = {"phone": "+91123", "state": "awaiting_language",
                    "name": "Ramrao", "district": "latur", "crops": ["cotton"],
                    "preferred_language": "en", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        with patch("src.handlers.onboarding._persist_to_db", new_callable=AsyncMock):
            response = await handle("+91123", "2")
    assert "Registration complete" in response


@pytest.mark.asyncio
async def test_language_marathi_text_accepted():
    session_data = {"phone": "+91123", "state": "awaiting_language",
                    "name": "सुभाष", "district": "jalna", "crops": ["tur"],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        with patch("src.handlers.onboarding._persist_to_db", new_callable=AsyncMock):
            response = await handle("+91123", "मराठी")
    assert "नोंदणी पूर्ण" in response


# ---------------------------------------------------------------------------
# STOP from any state
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stop_marathi_from_awaiting_name():
    session_data = {"phone": "+91123", "state": "awaiting_name",
                    "name": None, "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": True}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        with patch("src.handlers.onboarding._log_consent_event", new_callable=AsyncMock):
            response = await handle("+91123", "थांबा")
    assert "opted out" in response.lower() or "वगळण्यात" in response


@pytest.mark.asyncio
async def test_band_marathi_stop_command():
    cm, _ = _make_redis_mock()
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        with patch("src.handlers.onboarding._log_consent_event", new_callable=AsyncMock):
            response = await handle("+91123", "बंद")
    assert "opted out" in response.lower() or "वगळण्यात" in response


@pytest.mark.asyncio
async def test_stop_uppercase_english():
    cm, _ = _make_redis_mock()
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        with patch("src.handlers.onboarding._log_consent_event", new_callable=AsyncMock):
            response = await handle("+91999", "STOP")
    assert "opted out" in response.lower() or "वगळण्यात" in response


# ---------------------------------------------------------------------------
# DELETE from any state
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_marathi_triggers_confirmation():
    cm, _ = _make_redis_mock()
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "माझा डेटा हटवा")
    assert "DELETE CONFIRM" in response


@pytest.mark.asyncio
async def test_delete_english_triggers_confirmation():
    cm, _ = _make_redis_mock()
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91999", "delete my data")
    assert "DELETE CONFIRM" in response


# ---------------------------------------------------------------------------
# Already opted-out user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_opted_out_user_gets_rejoin_message():
    session_data = {"phone": "+91123", "state": "opted_out",
                    "name": None, "district": None, "crops": [],
                    "preferred_language": "mr", "consent_given": False}
    cm, _ = _make_redis_mock(session_data)
    with patch("src.handlers.onboarding.aioredis.from_url", return_value=cm):
        response = await handle("+91123", "सोयाबीन भाव")
    assert "Hi" in response or "opted out" in response.lower() or "बाहेर" in response
