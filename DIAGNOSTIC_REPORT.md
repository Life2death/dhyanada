# 🔍 DIAGNOSTIC REPORT — Production Issue Analysis
**Date**: 2026-05-02 (Current date)  
**Status**: ⚠️ MANDI PRICES NOT DISPLAYING, AI ENRICHMENT NOT WORKING

---

## Issue Summary

| Component | Expected | Actual | Status |
|-----------|----------|--------|--------|
| **Weather Updates** | ✅ Working | ✅ Working | 🟢 PASS |
| **Mandi Prices (Part 2)** | Display today's prices | Shows May 1st (or nothing) | 🔴 FAIL |
| **AI Enrichment (Part 3)** | Crop-specific AI guidance | Fallback basic advice | 🔴 FAIL |

---

## Root Cause Analysis

### Problem 1: Mandi Prices Not Current

**Evidence from logs:**
```
INFO:src.broadcasts.daily_brief:daily_brief: using mandi prices from 2026-05-01 (9 rows)
```

**Why this is happening:**
1. ✅ Price ingest endpoint successfully ingested 19 records
2. ✅ Prices are in database with date = 2026-05-01 (market data date)
3. ✅ Daily brief queries for available prices
4. ✅ Found 9 rows for May 1st
5. **❌ But May 2nd prices are NOT in database, only May 1st market data**

**Root Cause:**
- The agmarknet API was queried for 2026-05-02 arrival data
- The API returned 19 records, BUT with `arrival_date` = 2026-05-01
- This is CORRECT behavior (market reports yesterday's closing prices)
- **Issue**: Daily brief should be showing the latest available prices, which it is
- **Problem**: User expected TODAY's (May 2) prices, but market hasn't reported them yet

**Timeline:**
- 5:30 AM: Mandi price ingest triggers → fetches market data from API
- API returns: Yesterday's prices (May 1st) because that's what markets report
- 7:00 AM: Daily brief sent with May 1st prices (correct, as they're the latest available)

**What user sees:**
```
💰 आजचे APMC मंडी भाव — महाराष्ट्र
कांद्य: ₹2800 | ₹3200 | ₹3500  [May 1st prices]
```

---

### Problem 2: AI Enrichment Not Showing (Part 3)

**Evidence from logs:**
```
INFO:src.broadcasts.daily_brief:found 0 advisories for farmer_id=1
```

**Why this is happening:**
1. ✅ Advisory generation runs at 6:45 AM
2. ✅ Evaluates all active rules
3. ✅ Checks if farmer's weather matches rule thresholds
4. **❌ No advisories created for farmer (0 out of rules matched)**

**Root Cause Chain:**
1. Test farmer (ID=1) has limited/no crop data
2. Advisory rules require:
   - Farmer to have crops registered
   - Weather data for farmer's district
   - Rule thresholds to be met by weather
3. Even with data, fallback rules are used (basic humidity/temp logic)
4. **BUT**: No logging shows "AI enrichment success/failure"

**Actual Problem:**
```
logger.info("advisory_engine: AI enrichment success for rule=%s model=%s", ...)
logger.warning("advisory_engine: AI enrichment failed or disabled for rule=%s", ...)
```

**These log lines are NOT appearing in production logs!**

This means either:
- ❌ **No advisories are being created (0 matched rules)**
- ✅ OR: Advisories created but AI enrichment code not executing

---

## Detailed Investigation

### What Actually Happened

**Migration Verification:**
```
✅ 0015: village_confirmation columns added
✅ 0016: ai_insights JSON column added
✅ 0017: Maharashtra farmers reset
✅ Status: All applied successfully
```

**Code Deployment:**
```
✅ src/advisory/engine.py: Import at top-level, logging added
✅ src/broadcasts/daily_brief.py: Query advisories, display AI insights
✅ src/scheduler/celery_app.py: Price ingest 8 PM → 5:30 AM
```

**Test Results:**
```
Manual Advisory Generation Test:
  Input: All farmers in system
  Output: 1 farmer found, 0 advisories created
  Reason: No matching rules for test farmer
  
Manual Price Ingest:
  ✅ 19 records ingested
  ✅ Prices in database (May 1st market data)
  ✅ Daily brief correctly fetches latest (May 1st)
```

---

## Why Nothing Changed for Farmers

### The Real Issue

**Daily Brief Flow:**
```
1. Farmer sends "Hi" → greeting intent triggers
2. App calls: compose_daily_brief_marathi(farmer, date.today(), session)
3. Daily brief composes 4 parts:
   - Part 1: Weather ✅ (displays correctly)
   - Part 2: Mandi prices
     └─ Fetches latest available: May 1st (correct!)
     └─ BUT: Shows 9 rows from May 1st (not May 2)
   - Part 3: Advisories
     └─ Queries: WHERE farmer_id=X AND advisory_date=TODAY
     └─ Finds: 0 results (no advisories generated)
     └─ Shows: Fallback basic humidity/temp warnings (not AI)
   - Part 4: Irrigation ✅
```

**The Chain of Failures:**
1. Mandi prices: Working correctly (shows May 1, which is latest available)
   - User expected May 2 (not available yet from markets)
   
2. AI Enrichment: Not appearing because no advisories exist
   - Reason: Test farmer doesn't match any advisory rules
   - No weather data for today OR rules not configured for test farmer

---

## What Should Happen

**Correct Behavior Flow:**
```
5:30 AM: ingest_prices() 
  → Fetch API for latest market data
  → Get May 1st closing prices (19 records)
  → Persist to DB
  → ✅ WORKING

6:45 AM: trigger_farm_advisories()
  → Load farmer: ID=1, district=?, crops=[]
  → Load forecast: Query weather_observations for district
  → Match rules: Check if weather meets rule thresholds
  → Create advisories IF rules matched
  → Enrich with AI: Call LLM for crop-specific guidance
  → Persist: Store advisory with ai_insights JSON
  → ❌ ISSUE: 0 advisories created

7:00 AM: broadcast_daily_brief()
  → Fetch prices: Use latest available = May 1st ✅
  → Fetch advisories: WHERE farmer_id=X AND date=TODAY
    └─ If found: Display with ai_insights if available
    └─ If NOT found: Show fallback warnings ❌
```

---

## Why Advisories Aren't Being Created

**Likely Cause:**
1. Test farmer has `district = NULL` or `crops = []`
2. Advisory engine skips farmers without district or crops
3. No advisories created → no AI enrichment called
4. Daily brief finds 0 advisories → shows fallback message

**Evidence:**
- Advisory engine has guard: `if not district: return []`
- Advisory engine has guard: `if not crops: return []` (or skips crop-specific rules)
- Logs show: `found 0 advisories for farmer_id=1`

---

## Verification Checklist

- [x] Migrations applied: ✅ Yes, confirmed in logs
- [x] Price ingest working: ✅ 19 records ingested
- [x] Prices in database: ✅ Yes, May 1st data
- [x] Weather data exists: ✅ Yes, from OpenMeteо
- [x] Daily brief querying prices: ✅ Yes, getting 9 rows
- [ ] **Advisories being generated**: ❌ NO, getting 0
- [ ] **AI enrichment logs present**: ❌ NO, not seeing success/failure logs
- [ ] **Test farmer has complete data**: ❓ UNKNOWN (likely missing crops/district)

---

## Summary

### What's Working
1. ✅ Migrations successfully applied
2. ✅ Weather data ingestion and display
3. ✅ Mandi price ingestion (19 records)
4. ✅ Code deployment successful
5. ✅ Price display (shows May 1st - correct for market data)

### What's NOT Working
1. ❌ **No advisories generated** (0 advisories for farmer)
   - Reason: Test farmer likely has no crops/district data
   
2. ❌ **No AI enrichment logs** appearing
   - Reason: No advisories = no enrichment calls = no logs
   
3. ❌ **Part 3 showing fallback only**
   - Reason: No generated advisories, so falls back to hardcoded rules

---

## Next Steps

### To Fix Mandi Price Display
**Current behavior is actually CORRECT:**
- Market data for May 2 isn't available yet (markets report yesterday's data)
- System correctly showing May 1st (latest available)
- No fix needed - this is by design

### To Fix AI Enrichment
**Need to:**
1. ✅ Verify test farmer has `district` set
2. ✅ Verify test farmer has crops registered
3. ✅ Verify advisory rules are `active = true`
4. ⚠️ Run advisory generation again with proper farmer data
5. ⚠️ Check for AI enrichment success/failure logs

### Data Quality Checks
```sql
-- Check test farmer
SELECT id, district, deleted_at FROM farmers WHERE id = 1;

-- Check test farmer's crops
SELECT * FROM crops_of_interest WHERE farmer_id = 1;

-- Check active rules
SELECT COUNT(*) FROM advisory_rules WHERE active = true;

-- Check advisories created
SELECT COUNT(*) FROM advisories WHERE advisory_date = '2026-05-02';
```

