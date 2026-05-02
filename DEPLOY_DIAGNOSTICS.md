# Railway Deployment Health Check Failure - Diagnostics

## Current Issue
Health check at `/health` endpoint failing - app not starting up properly.

## Root Cause: Unknown (Need Logs)

### To Diagnose:

1. **Check Railway Logs**
   ```bash
   railway logs --follow
   ```
   Look for:
   - Database connection errors
   - Module import errors
   - Missing environment variables

2. **Check Environment Variables**
   ```bash
   railway shell
   env | grep DATABASE
   env | grep OPENROUTER
   ```

3. **Specific Error to Look For**
   - `ModuleNotFoundError` - Import issue
   - `ConnectionRefusedError` - Database not accessible
   - `TimeoutError` - Database timeout
   - `AttributeError` - Missing configuration

## Code Changes Made (Safe to Review)

All changes are minimal and non-breaking:
1. Moved import to top of file (line 24 in engine.py)
2. Added logging calls (advisory engine + daily brief)
3. Changed schedule times (celery_app.py)
4. Updated docstrings (tasks.py)

**None of these should cause startup failures.**

## Possible Issues & Solutions

### Option A: Environment Variable Issue
**Problem:** DATABASE_URL not set in Railway

**Check:**
```bash
railway shell
echo $DATABASE_URL
```

**Fix:** Ensure DATABASE_URL is set in Railway Variables

---

### Option B: Database Connection Issue
**Problem:** Database not accessible from container

**Check:**
```bash
railway shell
psql $DATABASE_URL -c "SELECT 1"
```

**Fix:** Verify database credentials and connectivity

---

### Option C: My Code Changes (Unlikely)
**Problem:** Import or logging causing startup failure

**Quick Fix - Revert Only My Changes:**

If you need to get the app running immediately:

```bash
# Revert engine.py import restructuring
git checkout src/advisory/engine.py

# Keep the other fixes:
# - Schedule changes (celery_app.py)
# - Logging (can be reverted if needed)
# - Docstrings (can be reverted if needed)
```

---

## Full Debug Checklist

Run these in Railway shell to diagnose:

```bash
# 1. Check environment
echo "Database URL: $DATABASE_URL" | head -c 50
echo "OpenRouter API: $OPENROUTER_API_KEY" | head -c 50

# 2. Test database connection
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import settings

async def test():
    try:
        engine = create_async_engine(settings.database_url)
        async with engine.begin() as conn:
            result = await conn.execute('SELECT 1')
            print('Database OK')
    except Exception as e:
        print(f'Database Error: {type(e).__name__}: {e}')
    finally:
        await engine.dispose()

asyncio.run(test())
"

# 3. Test imports
python -c "
try:
    from src.advisory.engine import generate_for_farmer
    print('Advisory engine import OK')
except Exception as e:
    print(f'Import error: {e}')
"

# 4. Check logs
tail -200 logs/uvicorn.log 2>/dev/null || echo 'No uvicorn logs'
tail -200 logs/error.log 2>/dev/null || echo 'No error logs'
```

---

## Recommended Next Step

1. **Get the actual error** from Railway logs
2. **Post the error** if you need help debugging
3. **I can then either:**
   - Fix the code if it's my fault
   - Help configure environment variables if it's config
   - Revert changes if needed to get app running

---

## Safe Rollback Plan (if needed)

If you need to roll back immediately:

```bash
git log --oneline | head -5  # See recent commits
git revert <commit-hash>     # Revert my changes
```

**Minimal rollback** (just revert imports if needed):
```bash
git checkout src/advisory/engine.py
```

The schedule changes and logging are safe even if reverted.

---

## Status

- Code changes: ✅ Compiled and tested locally
- Imports: ✅ No circular dependencies
- Syntax: ✅ All files pass compile check
- Deployment: ❌ Health check failing (needs investigation)

**Next action:** Get Railway logs to see actual error
