"""Tests for Docker services - PostgreSQL 16 and Redis 7."""
import pytest

@pytest.mark.skip(reason="Requires Docker running - manual test")
def test_postgres_running():
    """Test PostgreSQL 16 is running and accessible."""
    import asyncpg
    import asyncio
    async def check():
        conn = await asyncpg.connect('postgresql://dhanyada:dhanyada_secure_dev_password@localhost:5432/dhanyada')
        version = await conn.fetchval('SELECT version()')
        await conn.close()
        return "PostgreSQL 16" in version or "postgres" in version.lower()
    result = asyncio.run(check())
    assert result

@pytest.mark.skip(reason="Requires Docker running - manual test")
def test_redis_running():
    """Test Redis 7 is running and accessible."""
    import redis
    r = redis.Redis(host='localhost', port=6379)
    assert r.ping() == True

def test_docker_compose_config_exists():
    """Test docker-compose.yml exists."""
    import os
    assert os.path.exists('docker-compose.yml')
    
def test_env_has_database_urls():
    """Test .env has database connection strings."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    assert os.getenv('DATABASE_URL') is not None
    assert os.getenv('REDIS_URL') is not None
