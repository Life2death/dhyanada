"""
Kisan AI FastAPI Application with WhatsApp Webhook.

This is the main entry point for the bot.
Run: uvicorn src.main:app --reload
"""

import logging
import os
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import json

from src.adapters.whatsapp import WhatsAppAdapter, WhatsAppConfig, init_adapter

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kisan AI",
    description="WhatsApp bot for Maharashtra farmers",
    version="1.0.0",
)

# Initialize WhatsApp adapter on startup
@app.on_event("startup")
async def startup_event():
    """Initialize WhatsApp adapter with credentials from .env"""
    try:
        config = WhatsAppConfig(
            phone_id=os.getenv("WHATSAPP_PHONE_ID", ""),
            token=os.getenv("WHATSAPP_TOKEN", ""),
            business_account_id=os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID"),
        )
        adapter = init_adapter(config)
        logger.info("✅ WhatsApp adapter initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize WhatsApp adapter: {e}")
        raise


# Data models for webhook
class WebhookMessage(BaseModel):
    """WhatsApp incoming message"""
    from_phone: str
    message_id: str
    message_text: Optional[str] = None
    message_type: str = "text"  # text, image, document, etc.


class WebhookResponse(BaseModel):
    """Response to incoming message"""
    status: str
    message: str


# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "Kisan AI Bot"}


# Webhook verification (Meta requires this)
@app.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """
    Verify webhook with Meta.
    
    Meta sends a GET request to verify the webhook URL.
    We must respond with the hub_challenge if token matches.
    """
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "kisan_webhook_token")
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("✅ Webhook verified by Meta")
        return hub_challenge
    
    logger.warning(f"❌ Invalid webhook verification attempt")
    raise HTTPException(status_code=403, detail="Invalid verification token")


# Webhook receiver
@app.post("/webhook/whatsapp")
async def receive_message(request: Request):
    """
    Receive incoming WhatsApp messages from Meta.
    
    Meta sends incoming messages as webhook POST requests.
    We parse, log, and route them for processing.
    """
    try:
        data = await request.json()
        logger.debug(f"Incoming webhook: {json.dumps(data, indent=2)}")
        
        # Extract message from Meta's webhook format
        # Meta sends: {"entry": [{"changes": [{"value": {"messages": [...]}}]}]}
        
        if "entry" not in data:
            return JSONResponse({"status": "received"}, status_code=200)
        
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Handle incoming messages
                for message in value.get("messages", []):
                    from_phone = message.get("from")
                    message_id = message.get("id")
                    message_type = message.get("type", "text")
                    
                    # Extract text content
                    text_content = ""
                    if message_type == "text":
                        text_content = message.get("text", {}).get("body", "")
                    
                    logger.info(f"📱 Message from {from_phone}: {text_content}")
                    
                    # TODO: Route to intent classifier
                    # For now, just acknowledge receipt
        
        # Always respond with 200 OK to acknowledge receipt
        return JSONResponse({"status": "received"}, status_code=200)
    
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500,
        )


# Status endpoint
@app.get("/status")
async def status():
    """Get bot status"""
    return {
        "status": "running",
        "whatsapp_connected": True,
        "phone_id": os.getenv("WHATSAPP_PHONE_ID"),
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
