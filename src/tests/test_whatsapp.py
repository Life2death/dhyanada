import pytest
from unittest.mock import AsyncMock, patch
from src.adapters.whatsapp import WhatsAppAdapter, WhatsAppConfig, init_adapter, get_adapter


@pytest.fixture
def whatsapp_config():
    """Test configuration"""
    return WhatsAppConfig(
        phone_id="1234567890",
        token="test_token_xyz",
        business_account_id="9876543210",
    )


@pytest.fixture
def mock_pywa():
    """Mock PyWa client"""
    with patch("src.adapters.whatsapp.WhatsApp") as mock:
        yield mock


def test_adapter_initialization(whatsapp_config, mock_pywa):
    """Test WhatsApp adapter initializes correctly"""
    adapter = WhatsAppAdapter(whatsapp_config)
    assert adapter.is_connected()
    assert adapter.config.phone_id == "1234567890"
    mock_pywa.assert_called_once()


def test_adapter_invalid_config():
    """Test adapter handles invalid config"""
    with patch("src.adapters.whatsapp.WhatsApp", side_effect=Exception("Auth failed")):
        with pytest.raises(Exception):
            WhatsAppAdapter(WhatsAppConfig(phone_id="", token=""))


@pytest.mark.asyncio
async def test_send_text_message(whatsapp_config, mock_pywa):
    """Test sending text message"""
    mock_client = AsyncMock()
    mock_client.send_message = AsyncMock(return_value="msg_123")
    mock_pywa.return_value = mock_client

    adapter = WhatsAppAdapter(whatsapp_config)
    msg_id = await adapter.send_text_message(to="919876543210", text="Hello!")
    
    assert msg_id == "msg_123"
    mock_client.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_marathi_text(whatsapp_config, mock_pywa):
    """Test sending Marathi text message (UTF-8 support)"""
    mock_client = AsyncMock()
    mock_client.send_message = AsyncMock(return_value="msg_marathi_456")
    mock_pywa.return_value = mock_client

    adapter = WhatsAppAdapter(whatsapp_config)
    marathi_text = "शेतकर्या साठी आज चे मंडी दर"
    msg_id = await adapter.send_text_message(to="919876543210", text=marathi_text)
    
    assert msg_id == "msg_marathi_456"
    # Verify send_message was called with the Marathi text
    call_kwargs = mock_client.send_message.call_args.kwargs
    assert call_kwargs['text'] == marathi_text
    print(f"✓ Marathi text transmitted successfully: {marathi_text}")


def test_singleton_adapter(whatsapp_config, mock_pywa):
    """Test adapter singleton pattern"""
    init_adapter(whatsapp_config)
    adapter = get_adapter()
    
    assert adapter is not None
    assert adapter.is_connected()


def test_adapter_not_connected():
    """Test adapter behavior when not connected"""
    config = WhatsAppConfig(phone_id="", token="")
    with patch("src.adapters.whatsapp.WhatsApp", return_value=None):
        adapter = WhatsAppAdapter(config)
        assert not adapter.is_connected()
