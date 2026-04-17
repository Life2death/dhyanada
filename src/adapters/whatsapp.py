"""WhatsApp Cloud API Adapter using PyWa v4.0.0"""

import logging
from typing import Optional, List
from dataclasses import dataclass
from pywa import WhatsApp, types

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppConfig:
    """WhatsApp client configuration"""
    phone_id: str
    token: str
    business_account_id: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None


class WhatsAppAdapter:
    """Thin wrapper around PyWa for Kisan AI bot"""

    def __init__(self, config: WhatsAppConfig):
        self.config = config
        self.client: Optional[WhatsApp] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize PyWa client"""
        try:
            kwargs = {"phone_id": self.config.phone_id, "token": self.config.token}
            if self.config.business_account_id:
                kwargs["business_account_id"] = self.config.business_account_id
            self.client = WhatsApp(**kwargs)
            logger.info("WhatsApp adapter initialized")
        except Exception as e:
            logger.error(f"Failed to init WhatsApp: {e}")
            raise

    async def send_text_message(self, to: str, text: str) -> Optional[str]:
        """Send text message (supports Marathi)"""
        try:
            if not self.client:
                return None
            msg_id = await self.client.send_message(to=to, text=text)
            logger.info(f"Message sent to {to}")
            return msg_id
        except Exception as e:
            logger.error(f"Send failed: {e}")
            raise

    def is_connected(self) -> bool:
        return self.client is not None


_adapter_instance: Optional[WhatsAppAdapter] = None


def init_adapter(config: WhatsAppConfig) -> WhatsAppAdapter:
    global _adapter_instance
    _adapter_instance = WhatsAppAdapter(config)
    return _adapter_instance


def get_adapter() -> Optional[WhatsAppAdapter]:
    return _adapter_instance

