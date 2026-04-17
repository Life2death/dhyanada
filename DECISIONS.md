# Architecture Decisions Log

Append-only log of module choices. Newest entries at the top.

Format:
- **YYYY-MM-DD — Module N: <name>**
 - Chose: `<library>` v<version>
 - Runner-up: `<library>`
 - Why: <one-line reason>
 - Trade-off accepted: <one line>
 - Evaluation: `vendor-research/NN-<name>.md`

---

- **2026-04-17 — Scope Change: Target Districts + Commodities**
  - Changed districts from Latur/Nanded/Jalna/Akola/Washim → **Pune, Ahilyanagar, Navi Mumbai, Mumbai, Nashik**
  - Changed commodities from soyabean/tur/cotton only → **ALL commodities** (no filter at ingestion, filter at query time)
  - Why: Western Maharashtra + Nashik onion belt is the higher-volume market; all-commodity strategy future-proofs queries
  - Trade-off accepted: Slightly more storage (~180 MB/year); eliminates re-ingestion cost when new commodities needed

- **2026-04-17 — Module 5: Intent Classifier**
  - Chose: Regex-first + Gemini 1.5 Flash fallback
  - Runner-up: LLM-only classification
  - Why: ~85% of farmer messages matched by compiled regex at ~0ms, free, deterministic. LLM only for UNKNOWN (~500ms, ~₹0.001/call)
  - Trade-off accepted: Regex patterns need maintenance as new message styles emerge; mitigated by LLM fallback
  - Implementation: `src/classifier/` — `intents.py`, `regex_classifier.py`, `llm_classifier.py`, `classify.py`
  - Marathi: Full Devanagari patterns in every intent (पाठवा=subscribe, कांदा=onion, तूर=tur, हो=yes standalone, etc.)

- **2026-04-17 — Module 4: Mandi Price Ingestion (4-source pipeline)**
  - Chose: data.gov.in Agmarknet API (backbone) + MSAMB scraper + NHRDF onion + Vashi APMC direct
  - Runner-up: data.gov.in API only
  - Why: No single source has full coverage. Agmarknet misses Vashi ~30% of days. NHRDF is the authoritative onion quote. MSAMB has deepest MH APMC list.
  - Trade-off accepted: 4 scrapers to maintain vs 1 API. Mitigated by isolation (each source fails independently, others continue)
  - Merge preference: nhrdf > msamb > agmarknet > vashi (onion); vashi > msamb > agmarknet (Vashi yard); msamb > agmarknet > vashi > nhrdf (default)
  - API key: data.gov.in free key stored as DATA_GOV_IN_API_KEY / AGMARKNET_API_KEY (both accepted)

- **2026-04-17 — Module 1: WhatsApp Cloud API Wrapper**
 - Chose: `pywa` v4.0.0
 - Runner-up: `heyoo`
 - Why: Production-stable, BSUID-migration ready, async-first, minimal dependencies (httpx only), active maintenance (Feb 2026), FastAPI integration
 - Trade-off accepted: Slightly more complex API than heyoo, but higher reliability for production and future Meta changes
 - Evaluation: `vendor-research/01-whatsapp-wrapper.md`
 - Marathi requirement: Noted. Templates, message text, and captions support UTF-8 Marathi natively. Transliteration module (Module 9) will handle Hinglish↔Marathi conversion
- **2026-04-17 — Module 3: Docker Compose (Postgres 16 + Redis 7)**
 - Chose: Official `postgres:16-alpine` + `redis:7-alpine`
 - Runner-up: Cloud-managed services (AWS RDS/ElastiCache - considered but defer to Module 6)
 - Why: Local development simplicity, same services for prod, Alpine images lightweight, built-in health checks
 - Trade-off accepted: Self-managed vs cloud (manageable for MVP, migrate to AWS later if needed)
 - Evaluation: `vendor-research/02-docker-compose.md`
 - Configuration: Named volumes for persistence, network isolation, environment-based config
