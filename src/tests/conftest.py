"""Shared pytest fixtures and configuration."""
import pytest


@pytest.fixture(autouse=True)
def no_env_required(monkeypatch):
    """Ensure tests run without a real .env file."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
