# 🐳 Docker Compose Setup Guide

## Module 3: PostgreSQL 16 + Redis 7

This guide shows how to start the database services for Kisan AI.

---

## Prerequisites

- Docker installed ([docker.com/download](https://www.docker.com/products/docker-desktop))
- Docker Compose (included with Docker Desktop)
- Verify installation:
  ```bash
  docker --version
  docker-compose --version
  ```

---

## Starting Services

### 1. Start PostgreSQL + Redis

```bash
cd ~/projects/kisan-ai
docker-compose up -d
```

You should see:
```
Creating kisan_ai_postgres ... done
Creating kisan_ai_redis ... done
```

### 2. Check Service Status

```bash
docker-compose ps
```

Expected output:
```
NAME                 STATUS              PORTS
kisan_ai_postgres    Up (healthy)        5432/tcp
kisan_ai_redis       Up (healthy)        6379/tcp
```

### 3. View Logs

```bash
# All services
docker-compose logs -f

# Just Postgres
docker-compose logs -f postgres

# Just Redis
docker-compose logs -f redis
```

---

## Testing Database Connections

### Test PostgreSQL Connection

```bash
# Using psql (if installed)
psql -h localhost -U kisan -d kisan_ai
# Password: kisan_secure_dev_password

# Or using Docker
docker-compose exec postgres psql -U kisan -d kisan_ai
```

Once connected, test:
```sql
\dt  -- List tables
SELECT version();  -- Check PostgreSQL version
CREATE TABLE test (id SERIAL PRIMARY KEY, name TEXT);
SELECT * FROM test;
DROP TABLE test;
\q  -- Quit
```

### Test Redis Connection

```bash
# Using redis-cli (if installed)
redis-cli -h localhost -p 6379

# Or using Docker
docker-compose exec redis redis-cli
```

Once connected, test:
```
PING  -- Should return PONG
SET key "Hello"
GET key
DEL key
EXIT
```

### Test from Python

```python
import asyncio
import asyncpg
import redis

async def test_postgres():
    conn = await asyncpg.connect(
        'postgresql://kisan:kisan_secure_dev_password@localhost:5432/kisan_ai'
    )
    version = await conn.fetchval('SELECT version()')
    print(f"✅ Postgres: {version[:50]}...")
    await conn.close()

def test_redis():
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.set('test', 'Hello')
    value = r.get('test')
    print(f"✅ Redis: {value}")
    r.delete('test')

# Run tests
asyncio.run(test_postgres())
test_redis()
```

---

## Database Migration (Alembic)

Once services are running, initialize the database schema:

```bash
# Run migrations
cd ~/projects/kisan-ai
alembic upgrade head

# Check migration status
alembic current
```

---

## Stopping Services

### Stop (data preserved)
```bash
docker-compose down
```

### Stop and delete volumes (data deleted)
```bash
docker-compose down -v
```

---

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Try removing and starting fresh
docker-compose down -v
docker-compose up -d
```

### Can't connect to PostgreSQL
```bash
# Verify service is healthy
docker-compose ps

# Check if port 5432 is available
netstat -an | grep 5432  # Windows: netstat -ano | findstr 5432
```

### Can't connect to Redis
```bash
# Verify Redis is running
docker-compose logs redis

# Check port 6379
netstat -an | grep 6379  # Windows: netstat -ano | findstr 6379
```

### Connection refused errors
- Wait 10-15 seconds for services to start (health checks need time)
- Check `.env` has correct credentials: `kisan_secure_dev_password`
- Verify ports are not already in use

---

## Configuration Files

- **docker-compose.yml** - Service definitions
- **.env** - Connection strings (loaded by app)
- **vendor-research/02-docker-compose.md** - Detailed design

---

## Security Notes (Development Only)

⚠️ These settings are for **local development only**:
- Default password: `kisan_secure_dev_password` (change in production!)
- No authentication for Redis (add in production)
- Port 5432/6379 exposed (firewall in production)

For production, use:
- Strong random passwords
- Redis AUTH configured
- Network isolation
- Cloud-managed databases (AWS RDS, Google Cloud SQL)

---

## What's Next?

Module 4: Mandi Price Ingestion
- Connect to Agmarknet API
- Store prices in PostgreSQL
- Cache in Redis

---

Happy developing! 🚀
