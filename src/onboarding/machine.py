"""Onboarding state machine."""
from __future__ import annotations

import logging
from typing import Optional

from src.onboarding.redis_store import OnboardingStore
from src.onboarding.states import OnboardingContext, OnboardingState
from src.onboarding import transitions

logger = logging.getLogger(__name__)


class OnboardingMachine:
    """Process farmer input, transition state, persist to Redis."""

    def __init__(self, store: Optional[OnboardingStore] = None):
        self.store = store or OnboardingStore()

    async def process(self, phone: str, user_input: str) -> tuple[OnboardingContext, str]:
        """
        Process input, transition state, return (updated context, reply).
        """
        user_input = user_input.strip()

        # Load or create
        ctx = await self.store.load(phone) or OnboardingContext(
            phone=phone,
            state=OnboardingState.NEW,
        )

        # Universal commands
        if user_input.upper() in ("STOP", "थांबा"):
            ctx.state = OnboardingState.OPTED_OUT
            await self.store.save(ctx)
            return ctx, "आपण सेवा थांबवली. — You've opted out."

        if user_input.upper() in ("DELETE", "माझा डेटा हटवा"):
            ctx.state = OnboardingState.ERASURE_REQUESTED
            await self.store.save(ctx)
            return ctx, "डेटा हटविण्याचा विनंती स्वीकारली. — Erasure request received."

        # State-specific transitions
        if ctx.state == OnboardingState.NEW:
            ctx, reply = transitions.to_awaiting_consent(ctx)
        elif ctx.state == OnboardingState.AWAITING_CONSENT:
            ctx, reply = transitions.from_awaiting_consent(ctx, user_input)
        elif ctx.state == OnboardingState.AWAITING_NAME:
            ctx, reply = transitions.from_awaiting_name(ctx, user_input)
        elif ctx.state == OnboardingState.AWAITING_DISTRICT:
            ctx, reply = transitions.from_awaiting_district(ctx, user_input)
        elif ctx.state == OnboardingState.AWAITING_TALUKA:
            ctx, reply = transitions.from_awaiting_taluka(ctx, user_input)
        elif ctx.state == OnboardingState.AWAITING_VILLAGE:
            ctx, reply = transitions.from_awaiting_village(ctx, user_input)
        elif ctx.state == OnboardingState.AWAITING_CROPS:
            ctx, reply = transitions.from_awaiting_crops(ctx, user_input)
        elif ctx.state == OnboardingState.AWAITING_LANGUAGE:
            ctx, reply = transitions.from_awaiting_language(ctx, user_input)
        elif ctx.state == OnboardingState.ACTIVE:
            reply = "आप आधीच सक्रिय आहात. — Already active."
        elif ctx.state in (OnboardingState.OPTED_OUT, OnboardingState.ERASURE_REQUESTED):
            reply = "आपली खाती अक्षम आहे. — Your account is inactive."
        else:
            reply = "Error: unknown state"

        await self.store.save(ctx)
        return ctx, reply
