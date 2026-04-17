"""
WhatsApp Webhook Message Handler.

Processes incoming WhatsApp messages from Meta.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IncomingMessage:
    """Parsed incoming WhatsApp message"""
    from_phone: str
    message_id: str
    message_type: str  # text, image, document, audio, location, etc.
    text: Optional[str] = None
    timestamp: Optional[str] = None
    
    def is_text(self) -> bool:
        return self.message_type == "text"
    
    def is_marathi(self) -> bool:
        """Check if message contains Marathi script"""
        if not self.text:
            return False
        # Simple heuristic: check for Devanagari script
        marathi_range = range(0x0900, 0x097F)  # Devanagari Unicode range
        return any(ord(c) in marathi_range for c in self.text)


def parse_webhook_message(webhook_data: Dict[str, Any]) -> list[IncomingMessage]:
    """
    Parse Meta's webhook JSON format into IncomingMessage objects.
    
    Meta sends: {"entry": [{"changes": [{"value": {"messages": [...]}}]}]}
    
    Args:
        webhook_data: Raw webhook JSON from Meta
    
    Returns:
        List of parsed IncomingMessage objects
    """
    messages = []
    
    try:
        for entry in webhook_data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                for msg_data in value.get("messages", []):
                    from_phone = msg_data.get("from")
                    message_id = msg_data.get("id")
                    message_type = msg_data.get("type", "text")
                    timestamp = msg_data.get("timestamp")
                    
                    text_content = None
                    if message_type == "text":
                        text_content = msg_data.get("text", {}).get("body")
                    
                    msg = IncomingMessage(
                        from_phone=from_phone,
                        message_id=message_id,
                        message_type=message_type,
                        text=text_content,
                        timestamp=timestamp,
                    )
                    messages.append(msg)
                    logger.info(f"✅ Parsed message from {from_phone}: {text_content}")
    
    except Exception as e:
        logger.error(f"❌ Error parsing webhook: {e}")
    
    return messages


async def handle_message(message: IncomingMessage) -> Dict[str, Any]:
    """
    Handle incoming message (placeholder for intent routing).
    
    Future modules will:
    - Route to intent classifier
    - Fetch mandi prices
    - Send templated responses
    
    Args:
        message: Parsed IncomingMessage
    
    Returns:
        Handler result dict
    """
    logger.info(f"📱 Handling message from {message.from_phone}")
    logger.info(f"   Type: {message.message_type}")
    if message.is_marathi():
        logger.info(f"   Language: Marathi (detected)")
    
    # TODO: Implement intent classification
    return {
        "status": "received",
        "message_id": message.message_id,
        "next_step": "intent_classification",
    }
