"""WhatsApp Webhook Message Handler.

Processes incoming WhatsApp messages from Meta and routes them through
the intent classifier.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.classifier.classify import classify
from src.classifier.intents import Intent, IntentResult

logger = logging.getLogger(__name__)


@dataclass
class IncomingMessage:
    """Parsed incoming WhatsApp message."""
    from_phone: str
    message_id: str
    message_type: str   # text, image, document, audio, location, etc.
    text: Optional[str] = None
    timestamp: Optional[str] = None

    def is_text(self) -> bool:
        return self.message_type == "text"

    def is_marathi(self) -> bool:
        """Check if message contains Marathi/Devanagari script (U+0900–U+097F)."""
        if not self.text:
            return False
        return any(0x0900 <= ord(c) <= 0x097F for c in self.text)


def parse_webhook_message(webhook_data: Dict[str, Any]) -> list[IncomingMessage]:
    """Parse Meta's nested webhook JSON into IncomingMessage objects.

    Meta sends:
      {"entry": [{"changes": [{"value": {"messages": [...]}}]}]}
    """
    messages: list[IncomingMessage] = []
    try:
        for entry in webhook_data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg_data in value.get("messages", []):
                    msg_type = msg_data.get("type", "text")
                    text_content: Optional[str] = None
                    if msg_type == "text":
                        text_content = msg_data.get("text", {}).get("body")

                    messages.append(IncomingMessage(
                        from_phone=msg_data.get("from", ""),
                        message_id=msg_data.get("id", ""),
                        message_type=msg_type,
                        text=text_content,
                        timestamp=msg_data.get("timestamp"),
                    ))
    except Exception as exc:
        logger.error("parse_webhook_message: error: %s", exc)
    return messages


async def handle_message(message: IncomingMessage) -> Dict[str, Any]:
    """Route an incoming message through intent classification and dispatch.

    Returns a result dict consumed by the webhook endpoint for logging/ack.
    """
    logger.info("handle_message: from=%s type=%s marathi=%s",
                message.from_phone, message.message_type, message.is_marathi())

    # Non-text messages (images, audio, etc.) — acknowledge and prompt for text.
    if not message.is_text() or not message.text:
        return {
            "status": "non_text",
            "message_id": message.message_id,
            "intent": Intent.UNKNOWN.value,
        }

    result: IntentResult = await classify(message.text)

    logger.info(
        "handle_message: intent=%s confidence=%.2f commodity=%s district=%s source=%s",
        result.intent.value, result.confidence,
        result.commodity, result.district, result.source,
    )

    return {
        "status": "classified",
        "message_id": message.message_id,
        "intent": result.intent.value,
        "confidence": result.confidence,
        "commodity": result.commodity,
        "district": result.district,
        "source": result.source,
        "needs_commodity": result.needs_commodity,
    }
