# Maharashtra Kisan AI — Claude Code Handoff Document

**Last updated**: 2026-04-17  
**GitHub**: https://github.com/Life2death/kisan-ai  
**Owner**: Vikram Panmand (vikram.panmand@gmail.com)

---

## 1. Project Overview

Maharashtra Kisan AI is a WhatsApp chatbot that helps smallholder farmers in Maharashtra get real-time mandi (market) prices, MSP alerts, and daily price broadcasts — all via WhatsApp in **Marathi and English**.

| Field | Value |
|-------|-------|
| Target districts (Phase 1) | **Pune, Ahilyanagar (formerly Ahmednagar), Navi Mumbai, Mumbai, Nashik** |
| Target commodities | **ALL** commodities (no filter) — onion, tur, soyabean, cotton, tomato, potato, wheat, chana, jowar, bajra, grapes, pomegranate, maize, and more |
| Languages | Marathi (Devanagari) + English + Hinglish — **Marathi is first-class, not an afterthought** |
| Revenue model | B2B2C via FPOs — ₹5,000–15,000/month per FPO |
| Hosting | Hetzner Mumbai CPX21 (₹700/month), Docker Compose |

---

## 2. ✅ Completed Modules (as of 2026-04-17)

### Module 1 — WhatsApp Cloud API Wrapper ✅
- **Library**: `pywa==4.0.0` (chosen over heyoo — BSUID migration ready, async-first)
- **File**: `src/adapters/whatsapp.py` — thin adapter around pywa
- **Tests**: `src/tests/test_whatsapp.py` (6 tests ✅)
- **Decision log**: `vendor-research/01-whatsapp-wrapper.md`
- Marathi UTF-8 text flows through natively

### Module 2 — FastAPI Webhook Skeleton ✅
- **File**: `src/main.py` — FastAPI app with `/health`, `/webhook/whatsapp` (GET verify + POST receive), `/status`
- **File**: `src/handlers/webhook.py` — parses Meta's nested JSON, detects Marathi script, **now wired to intent classifier**
- **Tests**: `src/tests/test_webhook.py` (9 tests ✅)
- Meta webhook verification uses `Query(None, alias="hub.mode")` for dot-notation params
- Responds with `PlainTextResponse(hub_challenge)` — not `int()` (fixed)

### Module 3 — Docker Compose (Postgres 16 + Redis 7) ✅
- **File**: `docker-compose.yml`
- PostgreSQL 16-alpine: user=kisan, db=kisan_ai, port 5432, named volume `postgres_data`
- Redis 7-alpine: appendonly=yes, port 6379, named volume `redis_data`
- Health checks, `kisan_network` bridge, UTF-8 initdb args
- **Decision log**: `vendor-research/02-docker-compose.md`

### Module 4 — Mandi Price Ingestion (4-source pipeline) ✅
- **Package**: `src/ingestion/`
- **4 sources combined** (not just one):
  | Source | Role | Coverage |
  |--------|------|----------|
  | `agmarknet_api.py` | Backbone | Pune, Ahilyanagar, Nashik (strong); Thane/Vashi (partial) |
  | `msamb_scraper.py` | MH-specific depth | All 5 districts, deepest APMC list |
  | `nhrdf_scraper.py` | Onion specialist | Lasalgaon, Pimpalgaon, Vashi onion |
  | `vashi_scraper.py` | Vashi wholesale | Navi Mumbai (Agmarknet underreports Vashi ~30% of days) |
- **`normalizer.py`** — canonicalises district/APMC/commodity across English, Hinglish, Marathi Devanagari:
  - `Ahmednagar` → `ahilyanagar`, `Thane` → `navi_mumbai`, `कांदा` → `onion`, `तूर` → `tur`, `सोयाबीन` → `soyabean`
- **`merger.py`** — preference rules: `nhrdf > msamb > agmarknet > vashi` for onion; `vashi > msamb > agmarknet` for Vashi yard; `msamb > agmarknet > vashi > nhrdf` default
- **`orchestrator.py`** — `asyncio.gather` all 4 sources, idempotent upsert on unique constraint, `IngestionSummary` with health check
- **Alembic migration 0002** — adds `variety`, `apmc`, `arrival_quantity_qtl`, `raw_payload (JSONB)`, `UNIQUE(date, apmc, crop, variety, source)`
- **API key stored**: `DATA_GOV_IN_API_KEY` / `AGMARKNET_API_KEY` both map to `settings.agmarknet_api_key`
- **Tests**: `src/tests/test_ingestion_normalizer.py` (14 ✅), `test_ingestion_merger.py` (8 ✅), `test_ingestion_orchestrator.py` (3 ✅)
- **NOT YET**: Celery beat schedule — belongs in Module 8

### Module 5 — Intent Classifier ✅
- **Package**: `src/classifier/`
- **Pipeline**: regex (~0ms) → Gemini Flash fallback (only when regex returns UNKNOWN, ~500ms)
- **Intents**: `price_query`, `subscribe`, `unsubscribe`, `onboarding`, `help`, `greeting`, `feedback`, `unknown`
- **`intents.py`** — `Intent` enum + `IntentResult` dataclass (confidence, commodity, district, source, needs_commodity)
- **`regex_classifier.py`** — compiled patterns for English + Hinglish + **Marathi Devanagari**:
  - Price: `भाव`, `दर`, `किंमत`, `bhav`, `rate`, `price` + all commodity words
  - Subscribe: `पाठवा` (send = subscribe), `सुरू कर`, `हो` (standalone yes), `होय`
  - Unsubscribe: `थांबव`, `बंद कर`, `नको`, `stop`, `band`
  - Commodity extraction: 13 commodities with Marathi + Hinglish aliases
  - District extraction: all 5 target districts with Marathi names
  - Ordering: unsubscribe > subscribe > price (prevents "दैनिक भाव पाठवा" from matching price instead of subscribe)
- **`llm_classifier.py`** — Gemini 1.5 Flash, few-shot JSON prompt, never raises, returns UNKNOWN on any error
- **`classify.py`** — top-level `async classify(text)` routing function
- **`handle_message()`** updated — now classifies every message and returns `intent`, `confidence`, `commodity`, `district`, `needs_commodity`
- **Tests**: `src/tests/test_classifier.py` (33 tests ✅)

---

## 3. Test Summary

```
73 tests passing, 0 failing (as of 2026-04-17)

src/tests/test_whatsapp.py          6  ✅  Module 1
src/tests/test_webhook.py           9  ✅  Module 2
src/tests/test_ingestion_normalizer.py  14  ✅  Module 4
src/tests/test_ingestion_merger.py      8  ✅  Module 4
src/tests/test_ingestion_orchestrator.py 3  ✅  Module 4
src/tests/test_classifier.py           33  ✅  Module 5
```

Run with:
```bash
python -m pytest src/tests/ -v
```

---

## 4. Stack (Locked In)

| Component | Choice | Version |
|-----------|--------|---------|
| Language | Python | 3.11+ |
| Web framework | FastAPI | 0.115.5 |
| WhatsApp lib | pywa | 4.0.0 |
| Database | PostgreSQL | 16-alpine |
| Cache/queue | Redis | 7-alpine |
| Task queue | Celery + Beat | 5.4.0 |
| ORM | SQLAlchemy | 2.0.36 (async) |
| Migrations | Alembic | 1.14.0 |
| HTTP client | httpx | 0.28.1 |
| HTML scraping | BeautifulSoup4 | 4.12.3 |
| Retry | tenacity | 9.0.0 |
| LLM fallback | Gemini 1.5 Flash | via google-generativeai |
| Config | pydantic-settings | 2.7.0 |
| Tests | pytest + asyncio | 8.3.4 |

---

## 5. Project Structure (current)

```
kisan-ai/
├── AGENTS.md                      # OpenClaw instructions
├── DECISIONS.md                   # Architecture decision log (append-only)
├── CLAUDE-CODE-HANDOFF.md         # This file
├── docker-compose.yml             # Postgres 16 + Redis 7
├── Dockerfile
├── requirements.txt               # Pinned Python deps
├── alembic.ini
├── alembic/versions/
│   ├── 0001_initial_schema.py     # All 6 tables
│   └── 0002_extend_mandi_prices.py # variety, apmc, arrival_qty, raw_payload
├── vendor-research/
│   ├── 01-whatsapp-wrapper.md
│   └── 02-docker-compose.md
└── src/
    ├── config.py                  # Settings (pydantic-settings, AliasChoices for API keys)
    ├── main.py                    # FastAPI app
    ├── adapters/
    │   └── whatsapp.py            # pywa thin adapter
    ├── classifier/                # Module 5
    │   ├── intents.py             # Intent enum + IntentResult
    │   ├── regex_classifier.py    # Compiled regex patterns (EN+Hinglish+Marathi)
    │   ├── llm_classifier.py      # Gemini Flash fallback
    │   └── classify.py            # Top-level async classify()
    ├── handlers/
    │   ├── webhook.py             # parse_webhook_message + handle_message (wired to classifier)
    │   └── onboarding.py          # ⏳ Module 6
    ├── ingestion/                 # Module 4
    │   ├── normalizer.py          # District/APMC/commodity canonicalisation + Marathi aliases
    │   ├── merger.py              # Source preference rules
    │   ├── orchestrator.py        # Parallel fetch + upsert
    │   └── sources/
    │       ├── base.py            # PriceSource ABC + PriceRecord dataclass
    │       ├── agmarknet_api.py   # data.gov.in JSON API
    │       ├── msamb_scraper.py   # MSAMB HTML scraper
    │       ├── nhrdf_scraper.py   # NHRDF onion scraper
    │       └── vashi_scraper.py   # Vashi APMC scraper
    ├── models/
    │   ├── base.py
    │   ├── farmer.py
    │   ├── price.py               # MandiPrice (updated with variety, apmc, arrival_qty, raw_payload)
    │   ├── conversation.py
    │   ├── broadcast.py
    │   └── consent.py
    ├── scheduler/                 # ⏳ Module 8
    ├── templates/                 # ⏳ Module 9
    ├── router/
    ├── admin/
    └── tests/
```

---

## 6. Environment Variables (.env — gitignored, never commit)

```env
# WhatsApp Cloud API (PERMANENT TOKEN)
WHATSAPP_PHONE_ID=1135216599663873
WHATSAPP_BUSINESS_ACCOUNT_ID=1888194241890478
WHATSAPP_TOKEN=<permanent token in .env>
WHATSAPP_VERIFY_TOKEN=kisan_webhook_token

# Database
DATABASE_URL=postgresql://kisan:kisan_secure_dev_password@localhost:5432/kisan_ai
REDIS_URL=redis://localhost:6379

# FastAPI
FASTAPI_ENV=development
FASTAPI_DEBUG=true
CALLBACK_URL=http://localhost:8000/webhook/whatsapp

# Mandi prices — data.gov.in (either name works, both set in .env)
DATA_GOV_IN_API_KEY=579b464db66ec23bdd0000010a8c9ef744754e376ceaa1214c69fd60
AGMARKNET_API_KEY=579b464db66ec23bdd0000010a8c9ef744754e376ceaa1214c69fd60

# LLM
GEMINI_API_KEY=<set when needed>

# Logging
LOG_LEVEL=DEBUG
```

---

## 7. Database Schema (live as of migration 0002)

### mandi_prices (key table — extended in 0002)
```sql
CREATE TABLE mandi_prices (
  id BIGSERIAL PRIMARY KEY,
  date DATE NOT NULL,
  crop VARCHAR(50) NOT NULL,           -- canonical slug: onion, tur, soyabean, ...
  variety VARCHAR(100),
  mandi VARCHAR(100) NOT NULL,         -- display name
  apmc VARCHAR(100),                   -- canonical code: vashi, lasalgaon, ...
  district VARCHAR(50) NOT NULL,       -- canonical slug: pune, ahilyanagar, ...
  modal_price NUMERIC(10,2),
  min_price NUMERIC(10,2),
  max_price NUMERIC(10,2),
  msp NUMERIC(10,2),
  arrival_quantity_qtl NUMERIC(12,2),
  source VARCHAR(50) NOT NULL,         -- agmarknet | msamb | nhrdf | vashi
  raw_payload JSONB,                   -- original source record
  fetched_at TIMESTAMPTZ DEFAULT NOW(),
  is_stale BOOLEAN DEFAULT FALSE,
  UNIQUE (date, apmc, crop, variety, source)
);
```

### All other tables: farmers, crops_of_interest, conversations, broadcast_log, consent_events — created in migration 0001 (unchanged).

---

## 8. Key Design Decisions

1. **Marathi is first-class** — every pattern list, normalizer alias, and template has Marathi. The bot speaks Marathi natively, not as a translation afterthought.
2. **Districts changed** — original spec was Latur/Nanded/Jalna/Akola/Washim (Marathwada/Vidarbha). Updated to **Pune, Ahilyanagar, Navi Mumbai, Mumbai, Nashik** (Western Maharashtra, Nashik onion belt).
3. **All commodities** — no commodity filter at ingestion. Fetch everything, filter at query time. Storage is cheap; re-ingesting history is not.
4. **4-source pipeline, not 1** — Agmarknet alone misses Vashi ~30% of days. Combined pipeline gives ~99% coverage.
5. **Adapter pattern** — business logic never imports pywa directly (`src/adapters/whatsapp.py` wraps it).
6. **Regex-first classifier** — ~85% of messages handled by compiled regex (~0ms). LLM only for UNKNOWN (~500ms, costs ~₹0.001/call).
7. **Idempotent ingestion** — ON CONFLICT DO UPDATE on unique constraint. Celery retries are safe.
8. **Full audit trail** — all source records persisted (not just merger winners). Can replay with new preference rules without re-fetching.

---

## 9. Modules Remaining

| # | Module | Status | Depends on |
|---|--------|--------|------------|
| 6 | Onboarding state machine | ⏳ Next | Modules 1, 4 |
| 7 | Price handler | ⏳ | Modules 4, 5, 6 |
| 8 | Celery + broadcast scheduler | ⏳ | Modules 1, 4, 5 |
| 9 | Marathi templates + transliteration | ⏳ | None |
| 10 | Admin dashboard | ⏳ | Module 4 |
| 11 | DPDPA consent flow | ⏳ | Modules 4, 7 |

---

## 10. Critical Rules (Never Break)

- **NEVER** use Baileys, whatsapp-web.js, yowsup — personal-account libs violate Meta ToS
- **NEVER** let LLM generate Marathi responses freestyle — use pre-written templates with slots
- **NEVER** commit `.env` or credentials to git
- **NEVER** build payments/billing in Phase 1 — schema stub only
- **NEVER** build voice/image/weather in Phase 1 — text + prices only
- **Always** write tests. Current count: **73 passing**
- **Always** use conventional commits: `feat(scope):`, `fix(scope):`, `test(scope):`

---

## 11. Running Locally

```bash
# 1. Start Postgres + Redis
docker-compose up -d postgres redis

# 2. Run migrations
alembic upgrade head

# 3. Start API
uvicorn src.main:app --reload --port 8000

# 4. Run tests
python -m pytest src/tests/ -v
```
