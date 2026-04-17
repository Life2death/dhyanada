"""Redis-backed session store for OnboardingContext."""
from __future__ import annotations

import json
import logging
from typing import Optional

import redis

from src.config import settings
from src.onboarding.states import OnboardingContext, OnboardingState

logger = logging.getLogger(__name__)

_REDIS_KEY_PREFIX = "onboarding:"
_SESSION_TTL_SECONDS = 86400  # 24 hours


class OnboardingStore:
    """Load/save OnboardingContext to/from Redis."""

    def __init__(self, redis_url: str = settings.redis_url):
        self.redis = redis.from_url(redis_url, decode_responses=True)

    def _key(self, phone: str) -> str:
        return f"{_REDIS_KEY_PREFIX}{phone}"

    async def load(self, phone: str) -> Optional[OnboardingContext]:
        """Load context, or None if not found or expired (TTL)."""
        try:
            data = self.redis.get(self._key(phone))
            if not data:
                return None
            return OnboardingContext.from_dict(json.loads(data))
        except Exception as exc:
            logger.error("redis_store: load failed for %s: %s", phone, exc)
            return None

    async def save(self, ctx: OnboardingContext) -> bool:
        """Save context with 24h TTL."""
        try:
            ctx.last_updated_at = ctx.last_updated_at.__class__.now(ctx.last_updated_at.tzinfo)
            self.redis.setex(
                self._key(ctx.phone),
                _SESSION_TTL_SECONDS,
                json.dumps(ctx.to_dict()),
            )
            return True
        except Exception as exc:
            logger.error("redis_store: save failed for %s: %s", ctx.phone, exc)
            return False

    async def delete(self, phone: str) -> bool:
        """Explicitly clear session (for opted-out farmers)."""
        try:
            self.redis.delete(self._key(phone))
            return True
        except Exception as exc:
            logger.error("redis_store: delete failed for %s: %s", phone, exc)
            return False
