"""Thin adapter wrapping pywa. Business logic must never import pywa directly."""
import logging
from typing import Callable, Awaitable

from fastapi import FastAPI
from pywa import WhatsApp
from pywa.types import Message, CallbackButton, CallbackSelection

from src.config import settings

logger = logging.getLogger(__name__)


class WhatsAppAdapter:
    """Wraps pywa.WhatsApp; provides send/receive methods used by handlers."""

    def __init__(self) -> None:
        self._client: WhatsApp | None = None

    @property
    def is_ready(self) -> bool:
        return self._client is not None

    async def start(self, app: FastAPI) -> None:
        """Bind pywa to the FastAPI app and register handlers."""
        self._client = WhatsApp(
            phone_id=settings.whatsapp_phone_id,
            token=settings.whatsapp_token,
            server=app,
            verify_token=settings.whatsapp_verify_token,
            app_id=int(settings.whatsapp_app_id) if settings.whatsapp_app_id else None,
            app_secret=settings.whatsapp_app_secret,
        )
        logger.info("WhatsApp adapter initialised (phone_id=%s)", settings.whatsapp_phone_id)

    # ------------------------------------------------------------------
    # Outbound helpers
    # ------------------------------------------------------------------

    async def send_text(self, to: str, text: str) -> str:
        """Send a plain text message. Returns the WhatsApp message ID."""
        if not self._client:
            raise RuntimeError("WhatsApp adapter not started")
        return self._client.send_message(to=to, text=text)

    async def send_template(self, to: str, template_name: str, **kwargs) -> str:
        """Send a pre-approved WhatsApp template message."""
        if not self._client:
            raise RuntimeError("WhatsApp adapter not started")
        return self._client.send_template(to=to, template=template_name, **kwargs)

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def on_message(self, handler: Callable[[Message], Awaitable[None]]) -> None:
        """Register an async callback for inbound text messages."""
        if not self._client:
            raise RuntimeError("WhatsApp adapter not started")
        self._client.on_message(handler)

    def on_button(self, handler: Callable[[CallbackButton], Awaitable[None]]) -> None:
        """Register an async callback for button-click events."""
        if not self._client:
            raise RuntimeError("WhatsApp adapter not started")
        self._client.on_callback_button(handler)


# Module-level singleton — import this everywhere
wa_adapter = WhatsAppAdapter()
