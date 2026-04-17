# 02 - Docker Compose Setup — PostgreSQL 16 + Redis 7

**Evaluation Date**: 2026-04-17
**Decision**: Use official Docker images with best-practice configuration

## Context

Module 3 requires setting up local development databases:
- PostgreSQL 16 (relational database for bot state, user data, mandi prices)
- Redis 7 (cache, message queue, broadcast scheduler)

Unlike earlier modules, Docker Compose itself is the tool - we're configuring official images.

## Approach

1. Use **official Docker images**:
   - `postgres:16-alpine` (lightweight, ~150MB)
   - `redis:7-alpine` (lightweight, ~30MB)

2. Best practices:
   - Named volumes for persistence
   - Health checks for readiness
   - Environment variables for config
   - Network isolation

3. Integration with FastAPI:
   - SQLAlchemy ORM (already in requirements.txt: sqlalchemy==2.0.36)
   - asyncpg driver (already in requirements.txt: asyncpg==0.30.0)
   - Redis Python client (already in requirements.txt: redis==5.2.1)

## Configuration Details

### PostgreSQL 16

```yaml
image: postgres:16-alpine
environment:
  - POSTGRES_USER=kisan
  - POSTGRES_PASSWORD=kisan_secure_password  # CHANGE in production
  - POSTGRES_DB=kisan_ai
ports:
  - "5432:5432"
volumes:
  - postgres_data:/var/lib/postgresql/data
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U kisan"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Why Alpine**: Reduces image size, faster pulls, same functionality.

### Redis 7

```yaml
image: redis:7-alpine
ports:
  - "6379:6379"
volumes:
  - redis_data:/data
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Commands saved**: Using `redis-cli --save` to persist data to disk.

## Why These Versions?

- **Postgres 16**: Latest stable, released Oct 2023. Better performance, JSONB improvements.
- **Redis 7**: Stable LTS version, ACL improvements, faster streams.

Both have 3+ year support windows (safe for production).

## Integration Points

| Component | Postgres | Redis |
|-----------|----------|-------|
| User profiles | ✅ | - |
| Conversations | ✅ | ✅ (cache) |
| Mandi prices | ✅ | ✅ (cache) |
| Broadcast queue | - | ✅ |
| Rate limiting | - | ✅ |
| Session cache | - | ✅ |

## Network

Docker Compose creates auto-linked network:
- FastAPI app: `http://localhost:5432` → Postgres
- FastAPI app: `http://localhost:6379` → Redis

## Persistence

Both use named volumes:
- `postgres_data:/var/lib/postgresql/data`
- `redis_data:/data`

Data survives `docker-compose down` (volumes persist).
Clear with `docker-compose down -v`.

## Production Readiness

- ✅ Health checks included
- ✅ Standard ports
- ✅ Named volumes
- ✅ Environment variable configuration
- ⚠️ Default passwords (change in production)

## Testing Strategy

1. Start services: `docker-compose up -d`
2. Wait for health checks: `docker-compose logs`
3. Connect from FastAPI app
4. Run migrations: `alembic upgrade head`
5. Verify data persists: `docker-compose down && docker-compose up`
