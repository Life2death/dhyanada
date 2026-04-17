"""Tests for Module 6 — onboarding state machine."""
from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from src.onboarding.states import OnboardingContext, OnboardingState
from src.onboarding.machine import OnboardingMachine


class TestOnboardingContext:
    def test_to_dict_and_from_dict(self):
        ctx = OnboardingContext(
            phone="919876543210",
            state=OnboardingState.AWAITING_NAME,
            consent_given=True,
            name="Rajesh",
            preferred_language="mr",
        )
        d = ctx.to_dict()
        assert d["state"] == "awaiting_name"
        ctx2 = OnboardingContext.from_dict(d)
        assert ctx2.state == OnboardingState.AWAITING_NAME
        assert ctx2.name == "Rajesh"

    def test_is_complete(self):
        ctx = OnboardingContext(
            phone="919876543210",
            state=OnboardingState.ACTIVE,
            consent_given=True,
            name="Rajesh",
            district="pune",
            crops=["onion", "tur"],
        )
        assert ctx.is_complete()

    def test_is_complete_missing_crops(self):
        ctx = OnboardingContext(
            phone="919876543210",
            state=OnboardingState.AWAITING_CROPS,
            consent_given=True,
            name="Rajesh",
            district="pune",
            crops=[],
        )
        assert not ctx.is_complete()


class TestOnboardingMachine:
    @pytest.mark.asyncio
    async def test_new_to_awaiting_consent(self):
        machine = OnboardingMachine(store=AsyncMock())
        machine.store.load.return_value = None
        ctx, reply = await machine.process("919876543210", "hello")
        assert ctx.state == OnboardingState.AWAITING_CONSENT
        assert "नमस्कार" in reply

    @pytest.mark.asyncio
    async def test_consent_yes_marathi(self):
        ctx = OnboardingContext(phone="919876543210", state=OnboardingState.AWAITING_CONSENT)
        machine = OnboardingMachine(store=AsyncMock())
        machine.store.load.return_value = ctx
        ctx, reply = await machine.process("919876543210", "हो")
        assert ctx.state == OnboardingState.AWAITING_NAME
        assert "नाव" in reply

    @pytest.mark.asyncio
    async def test_consent_no(self):
        ctx = OnboardingContext(phone="919876543210", state=OnboardingState.AWAITING_CONSENT)
        machine = OnboardingMachine(store=AsyncMock())
        machine.store.load.return_value = ctx
        ctx, reply = await machine.process("919876543210", "नाही")
        assert ctx.state == OnboardingState.OPTED_OUT

    @pytest.mark.asyncio
    async def test_name_entry(self):
        ctx = OnboardingContext(
            phone="919876543210",
            state=OnboardingState.AWAITING_NAME,
            consent_given=True,
        )
        machine = OnboardingMachine(store=AsyncMock())
        machine.store.load.return_value = ctx
        ctx, reply = await machine.process("919876543210", "राजेश")
        assert ctx.state == OnboardingState.AWAITING_DISTRICT
        assert ctx.name == "राजेश"

    @pytest.mark.asyncio
    async def test_district_pune(self):
        ctx = OnboardingContext(
            phone="919876543210",
            state=OnboardingState.AWAITING_DISTRICT,
            name="Rajesh",
            consent_given=True,
        )
        machine = OnboardingMachine(store=AsyncMock())
        machine.store.load.return_value = ctx
        ctx, reply = await machine.process("919876543210", "पुणे")
        assert ctx.state == OnboardingState.AWAITING_CROPS
        assert ctx.district == "pune"

    @pytest.mark.asyncio
    async def test_crops_english(self):
        ctx = OnboardingContext(
            phone="919876543210",
            state=OnboardingState.AWAITING_CROPS,
            name="Rajesh",
            consent_given=True,
            district="nashik",
        )
        machine = OnboardingMachine(store=AsyncMock())
        machine.store.load.return_value = ctx
        ctx, reply = await machine.process("919876543210", "onion tur")
        assert ctx.state == OnboardingState.AWAITING_LANGUAGE
        assert "onion" in ctx.crops
        assert "tur" in ctx.crops

    @pytest.mark.asyncio
    async def test_language_mr(self):
        ctx = OnboardingContext(
            phone="919876543210",
            state=OnboardingState.AWAITING_LANGUAGE,
            name="Rajesh",
            consent_given=True,
            district="pune",
            crops=["onion"],
        )
        machine = OnboardingMachine(store=AsyncMock())
        machine.store.load.return_value = ctx
        ctx, reply = await machine.process("919876543210", "MR")
        assert ctx.state == OnboardingState.ACTIVE
        assert ctx.preferred_language == "mr"

    @pytest.mark.asyncio
    async def test_stop_at_any_state(self):
        ctx = OnboardingContext(
            phone="919876543210",
            state=OnboardingState.AWAITING_CROPS,
            consent_given=True,
        )
        machine = OnboardingMachine(store=AsyncMock())
        machine.store.load.return_value = ctx
        ctx, reply = await machine.process("919876543210", "STOP")
        assert ctx.state == OnboardingState.OPTED_OUT

    @pytest.mark.asyncio
    async def test_delete_at_any_state(self):
        ctx = OnboardingContext(
            phone="919876543210",
            state=OnboardingState.AWAITING_NAME,
            consent_given=True,
        )
        machine = OnboardingMachine(store=AsyncMock())
        machine.store.load.return_value = ctx
        ctx, reply = await machine.process("919876543210", "DELETE")
        assert ctx.state == OnboardingState.ERASURE_REQUESTED
