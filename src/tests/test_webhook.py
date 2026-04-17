"""Tests for WhatsApp webhook receiver."""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.handlers.webhook import parse_webhook_message, IncomingMessage


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_verification(client):
    """Test Meta webhook verification (GET request)"""
    response = client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "test_challenge_123",
            "hub.verify_token": "kisan_webhook_token",
        }
    )
    assert response.status_code == 200
    # Response contains the challenge value
    assert "test_challenge_123" in response.text


def test_webhook_verification_invalid_token(client):
    """Test webhook verification with invalid token"""
    response = client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "test_challenge",
            "hub.verify_token": "wrong_token",
        }
    )
    assert response.status_code == 403


def test_webhook_receive_text_message(client):
    """Test receiving a text message from WhatsApp"""
    webhook_data = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "msg_123",
                                    "type": "text",
                                    "text": {"body": "नमस्कार"},
                                    "timestamp": "1234567890",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    response = client.post("/webhook/whatsapp", json=webhook_data)
    assert response.status_code == 200
    assert response.json()["status"] == "received"


def test_webhook_receive_empty_message(client):
    """Test receiving empty webhook (no messages)"""
    webhook_data = {"entry": []}
    response = client.post("/webhook/whatsapp", json=webhook_data)
    assert response.status_code == 200


def test_parse_webhook_message_text():
    """Test parsing text message from webhook"""
    webhook_data = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.123456",
                                    "type": "text",
                                    "text": {"body": "मंडी दर खांडा"},
                                    "timestamp": "1702912345",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    messages = parse_webhook_message(webhook_data)
    assert len(messages) == 1
    msg = messages[0]
    assert msg.from_phone == "919876543210"
    assert msg.message_id == "wamid.123456"
    assert msg.text == "मंडी दर खांडा"
    assert msg.message_type == "text"
    assert msg.is_text()


def test_parse_webhook_marathi_detection():
    """Test Marathi language detection"""
    msg = IncomingMessage(
        from_phone="919876543210",
        message_id="msg_1",
        message_type="text",
        text="शेतकर्याचे दर",
    )
    assert msg.is_marathi()
    
    msg_english = IncomingMessage(
        from_phone="919876543210",
        message_id="msg_2",
        message_type="text",
        text="Farmer rates",
    )
    assert not msg_english.is_marathi()


def test_parse_webhook_multiple_messages():
    """Test parsing multiple messages in single webhook"""
    webhook_data = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "msg_1",
                                    "type": "text",
                                    "text": {"body": "मंडी"},
                                },
                                {
                                    "from": "919876543210",
                                    "id": "msg_2",
                                    "type": "text",
                                    "text": {"body": "दर"},
                                },
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    messages = parse_webhook_message(webhook_data)
    assert len(messages) == 2
    assert messages[0].text == "मंडी"
    assert messages[1].text == "दर"


def test_status_endpoint(client):
    """Test status endpoint"""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["whatsapp_connected"] == True
