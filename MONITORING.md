# Phase 3 Step 3: Monitoring & Alerting — Implementation Guide

## ✅ Completed Infrastructure

### Database Models
- **`src/models/error_log.py`** — Persistent error logging with full stacktraces and context
- **`src/models/service_health.py`** — Real-time service health metrics and status tracking

### Core Services
- **`src/adapters/email.py`** — SMTP email adapter with HTML formatting and alert deduplication
- **`src/services/alert_service.py`** — Error logging, threshold checking, and alerting orchestration
- **`src/middleware/error_handler.py`** — Global exception handler that logs all errors to database

### Configuration
- **Updated `src/config.py`** — Added email and monitoring settings
- **Updated `.env`** — Email credentials and alert thresholds
- **Updated `src/main.py`** — Registered error middleware and enhanced `/health` endpoint

### Admin Dashboard Foundation
- **Updated `src/admin/repository.py`** — Added error query methods:
  - `get_error_summary()` — Error counts by service/type
  - `get_recent_errors()` — Last N errors
  - `get_service_health()` — Current health of all services
  - `get_error_timeline()` — Error trends over time

---

## 🚀 How It Works

### Error Flow
```
Incoming Request
  ↓
[ErrorLoggingMiddleware]
  ↓
Handler execution
  ↓
Exception? → ErrorLog saved to database
  ↓
AlertService checks thresholds
  ↓
Email alert sent if threshold exceeded
```

### Usage in Handlers

**Explicit error logging (optional):**
```python
from src.services.alert_service import AlertService

# In your handler
try:
    # do something
except Exception as e:
    await alert_service.log_error(
        service="whatsapp",
        error_type="api_error",
        message=str(e),
        stacktrace=traceback.format_exc(),
        context={"farmer_id": farmer_id}
    )
```

**Middleware does it automatically:**
- No changes needed to handlers
- All unhandled exceptions are logged automatically
- Middleware extracts context from request

---

## 📊 Admin Dashboard Access

**Check error logs:**
```bash
# Upcoming endpoints:
GET /admin/api/errors          # Recent errors
GET /admin/api/service-health  # Service status
GET /admin/api/alerts          # Alert history
```

**Dashboard tabs:**
- System Health — Service status cards (green/yellow/red)
- Error Logs — Recent errors with filtering
- Alerts — Alert history and resolutions

---

## 📧 Email Alert Setup

### For Gmail:
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer" (or your device)
3. Google generates a 16-character app password
4. Update `.env`:
   ```bash
   SMTP_USERNAME=your-gmail@gmail.com
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # 16-char app password
   ADMIN_EMAIL=your-gmail@gmail.com
   ```
5. Restart server

### Testing Email:
```python
# In Python shell or test script:
from src.adapters.email import EmailAdapter
from src.config import settings

email = EmailAdapter(
    smtp_host=settings.smtp_host,
    smtp_port=settings.smtp_port,
    smtp_username=settings.smtp_username,
    smtp_password=settings.smtp_password,
    admin_email=settings.admin_email,
)

import asyncio
asyncio.run(email.send_alert(
    subject="Test Alert",
    body="This is a test alert",
    alert_type="info"
))
```

---

## ⚙️ Configuration Reference

| Setting | Default | Purpose |
|---------|---------|---------|
| `SMTP_HOST` | smtp.gmail.com | Email server |
| `SMTP_PORT` | 587 | TLS port |
| `ADMIN_EMAIL` | (empty) | Alert recipient |
| `ALERT_ERROR_THRESHOLD` | 5.0 | % to trigger alert |
| `ALERT_COOLDOWN_MINUTES` | 60 | Dedup repeated alerts |
| `ERROR_RETENTION_DAYS` | 90 | Keep errors for 90 days |
| `HEALTH_CHECK_INTERVAL_MINUTES` | 60 | Run health checks hourly |

---

## 🔍 Querying Errors

### From Python:
```python
from src.services.alert_service import AlertService
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Create session
engine = create_async_engine(settings.database_url)
async_session = sessionmaker(engine, class_=AsyncSession)

async with async_session() as session:
    alert_svc = AlertService(session)
    
    # Get error rate for weather service (past hour)
    rate = await alert_svc.get_error_rate("weather", hours=1)
    
    # Get recent errors
    errors = await alert_svc.get_recent_errors("whatsapp", limit=10)
    
    # Get summary
    summary = await alert_svc.get_error_summary(hours=24)
```

### From Admin Dashboard:
```python
from src.admin.repository import AdminRepository

async with async_session() as session:
    repo = AdminRepository(session)
    
    # Get all service health
    health = await repo.get_service_health()
    
    # Get recent errors
    errors = await repo.get_recent_errors(limit=50)
    
    # Get error trends
    timeline = await repo.get_error_timeline(hours=24)
```

---

## 🔧 Remaining Tasks (Quick Implementation)

### 1. Add Error API Endpoints (`src/admin/routes.py`)
```python
@router.get("/api/errors")
async def get_errors(admin: dict = Depends(get_admin_token)):
    repo = AdminRepository(session)
    errors = await repo.get_recent_errors()
    return {"errors": errors}

@router.get("/api/service-health")
async def get_service_health(admin: dict = Depends(get_admin_token)):
    repo = AdminRepository(session)
    health = await repo.get_service_health()
    return health
```

### 2. Create Health Check Tasks (`src/scheduler/health_checks.py`)
```python
async def check_whatsapp_health():
    # Try to send/receive a test message
    # Update ServiceHealth table
    
async def check_weather_health():
    # Try to fetch weather data
    # Update ServiceHealth table
    
# Schedule tasks via APScheduler or Celery
```

### 3. Update Dashboard HTML (`src/admin/routes.py`)
- Add "System Health" tab with service cards
- Add "Error Logs" tab with error table and filters
- Add "Alerts" tab with alert timeline

---

## 📋 Testing Checklist

- [ ] Start server: `python -m uvicorn src.main:app --reload`
- [ ] Check `/health` endpoint returns service status
- [ ] Trigger a test error in handler
- [ ] Verify error logged to `error_logs` table
- [ ] Check admin dashboard shows error
- [ ] Configure SMTP and send test email
- [ ] Verify alert email received
- [ ] Check alert deduplication (no spam within 1 hour)

---

## 🎯 Success Criteria

✅ All exceptions persist to database with stacktraces
✅ ServiceHealth updates via periodic health checks
✅ Email alerts sent when thresholds exceeded
✅ Admin dashboard shows error metrics and trends
✅ No PII leaked in error logs
✅ Errors auto-cleanup after 90 days
✅ Alert deduplication prevents spam

---

## 📚 Architecture Reference

**Error Log Storage:**
- Table: `error_logs` (indexes on service, error_type, created_at)
- Fields: service, error_type, message, stacktrace, context_json, created_at, resolved_at

**Service Health Storage:**
- Table: `service_health` (unique per service)
- Fields: service_name, is_healthy, error_rate_1h, error_rate_24h, avg_latency_ms, last_heartbeat

**Alert Flow:**
1. Error occurs → Middleware catches it
2. ErrorLog record created
3. AlertService checks ServiceHealth thresholds
4. EmailAdapter sends alert (if threshold exceeded & not in cooldown)
5. Admin gets notified

---

## 🚨 Alert Types

**By Severity:**
- `critical` — Service down, error rate > 5%
- `warning` — Degraded service, latency > 1000ms
- `info` — Service recovered, status update

**By Source:**
- Unhandled exceptions (via middleware)
- Health check failures (via health check tasks)
- Threshold violations (via AlertService)

---

## 📞 Support & Troubleshooting

### Email not sending?
- Check SMTP credentials in `.env`
- Verify Gmail app password (if using Gmail)
- Check email adapter logs: `logger.error()`

### Errors not logged?
- Verify `ErrorLog` table created (check database)
- Check middleware is registered in `main.py`
- Review logs for database connection errors

### Service health not updating?
- Health check tasks not yet implemented
- Manual test: `await alert_service.update_service_health(...)`

---

**Next Phase:** Phase 3 Step 4 (Production Deployment)
- Docker containerization
- CI/CD with GitHub Actions
- Kubernetes/cloud deployment
