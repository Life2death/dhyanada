"""Onboarding state machine — farmer signup via WhatsApp."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class OnboardingState(str, Enum):
    """Farmer signup progression states."""
    NEW = "new"                          # initial state
    AWAITING_CONSENT = "awaiting_consent"
    AWAITING_NAME = "awaiting_name"
    AWAITING_DISTRICT = "awaiting_district"
    AWAITING_CROPS = "awaiting_crops"
    AWAITING_LANGUAGE = "awaiting_language"
    ACTIVE = "active"                   # complete → write to Postgres
    OPTED_OUT = "opted_out"             # STOP at any state
    ERASURE_REQUESTED = "erasure_requested"  # DELETE at any state
    ERASED = "erased"                   # after 30-day hard delete


@dataclass(slots=True)
class OnboardingContext:
    """Mutable state during onboarding. Persisted in Redis."""

    phone: str
    state: OnboardingState
    consent_given: bool = False
    name: Optional[str] = None
    district: Optional[str] = None        # canonical slug: pune, ahilyanagar, ...
    crops: list[str] = field(default_factory=list)  # canonical slugs
    preferred_language: str = "mr"        # mr | en
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Serialize for Redis (JSON-safe)."""
        d = asdict(self)
        d["state"] = self.state.value
        d["created_at"] = self.created_at.isoformat()
        d["last_updated_at"] = self.last_updated_at.isoformat()
        return d

    @staticmethod
    def from_dict(data: dict) -> OnboardingContext:
        """Deserialize from Redis."""
        data["state"] = OnboardingState(data["state"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_updated_at"] = datetime.fromisoformat(data["last_updated_at"])
        return OnboardingContext(**data)

    def is_complete(self) -> bool:
        """True if all required fields filled."""
        return (
            self.consent_given
            and self.name
            and self.district
            and len(self.crops) > 0
        )

    def next_state(self) -> OnboardingState:
        """Compute next state based on what's filled."""
        if not self.consent_given:
            return OnboardingState.AWAITING_CONSENT
        if not self.name:
            return OnboardingState.AWAITING_NAME
        if not self.district:
            return OnboardingState.AWAITING_DISTRICT
        if not self.crops:
            return OnboardingState.AWAITING_CROPS
        return OnboardingState.AWAITING_LANGUAGE
