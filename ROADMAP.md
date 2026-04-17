# Kisan AI Roadmap

**Making real-time market intelligence available to every Maharashtra farmer — directly on WhatsApp.**

**Kisan AI** is a production-grade WhatsApp chatbot that delivers live mandi prices, weather advisories, pest diagnosis, government schemes, and more — in **Marathi + English** — to small and marginal farmers who only use WhatsApp.

### Vision
To become the **ultimate killer app for Maharashtra farmers** — the single WhatsApp contact they open every morning for:
- Accurate, multi-source mandi prices
- Voice + photo-based advice
- Daily proactive alerts
- Life-changing government scheme & insurance information
- Simple profit/loss tracking

No apps to download. No English needed. Zero cost for farmers.

---

## Current State (v0.2 — April 17, 2026)

**✅ Completed Modules**
- Module 1: WhatsApp Cloud API wrapper (`pywa` v4.0.0)
- Module 2: FastAPI webhook skeleton
- Module 3: Docker Compose (PostgreSQL 16 + Redis 7)
- Module 4: Multi-source mandi price ingestion pipeline  
  → Agmarknet API + MSAMB scraper + NHRDF (onion) + Vashi APMC direct feed
- Module 5: Intent classifier (Regex-first + Gemini 1.5 Flash fallback) with full Marathi Devanagari support

**✅ Infrastructure & Quality**
- Full Docker + docker-compose setup
- Alembic migrations ready
- 73+ passing tests (classifier + Marathi scenarios + onboarding)
- Strict git workflow + conventional commits
- DPDPA consent architecture documented

**Current Capabilities**
- Receives WhatsApp messages
- Detects Marathi automatically
- Ingests and stores live prices from 4 authoritative sources
- Fast, deterministic intent classification

**What is NOT live yet**  
→ Actual farmer replies, onboarding flow, daily broadcasts, and consent management.

**Repo Status**: Early but extremely solid foundation. Production-ready architecture already in place.

---

## Phase 1: MVP — "Daily Mandi Rates Bot" (Target: May 2026)

**Goal**: Make the bot **actually useful** for 1,000+ farmers within 4–6 weeks.

**Remaining Modules (in order)**
1. **Module 6**: Onboarding state machine (name, district, crops, consent)
2. **Module 7**: Price handler + rich WhatsApp replies (buttons + formatted tables)
3. **Module 8**: Celery + daily 6:30 AM IST price broadcast scheduler
4. **Module 9**: Marathi templates + Hinglish ↔ Marathi transliteration
5. **Module 10**: Basic admin dashboard (FastAPI + HTMX)
6. **Module 11**: Full DPDPA consent flow + audit logging + right-to-erasure

**Success Metrics**
- Farmers can onboard via WhatsApp
- Receive daily price broadcast
- Ask "कांदा दर पुणे" and get accurate reply
- 100% DPDPA compliant

---

## Phase 2: Smart Farmer Assistant (Target: June–July 2026)

**Goal**: Turn the bot into a **daily companion**.

**Key Features to Add**
- Voice message support (Meta native + Whisper/Marathi STT)
- Photo upload → hybrid pest & disease diagnosis  
  → Local TensorFlow model (top 20 pests) + Gemini Vision fallback
- Weather integration (IMD/OpenWeather) + combined price + weather advisory
- Government schemes & MSP alerts (PM-KISAN, crop insurance, subsidies)
- Price alerts ("notify me when onion > ₹5000")
- Conversation memory (Redis-based last 10 messages)

---

## Phase 3: Ultimate Killer for Farmers (Target: Aug–Oct 2026)

**This is where we become unbeatable.**

- Historical price charts (send as image)
- Simple bookkeeping & profit/loss tracker  
  ("Sold 10 quintal onion for 45000" → monthly summary)
- Climate-resilient advisory + district-specific recommendations
- Buyer matching / direct FPO connect (optional)
- Loan & insurance eligibility checker
- Video knowledge base (YouTube → summarized advice)
- Multi-language expansion (full Hinglish + Hindi)

**Differentiators vs every other agri-bot**
- Live multi-source prices (others use static data)
- Voice + photo native
- Hybrid (fast local + LLM) intelligence
- Fully production-grade (Docker, Postgres, Redis, Celery, DPDPA)
- Built for Maharashtra first, then scalable to all India

---

## Phase 4: Scale, Monetization & Impact (Q4 2026 onward)

- Cloud migration (AWS/Hetzner Mumbai)
- FPO & B2B2C partnerships (₹5k–15k/month per FPO)
- Premium tier (advanced alerts + analytics)
- Open analytics dashboard for farmers
- Community contributions & state expansion
- Potential social impact funding / government pilot

---

## How You Can Contribute

We follow a strict but simple process (see `AGENTS.md`):
1. One module at a time
2. License check + thin adapter pattern
3. Tests + documentation
4. Conventional commit + push to `main`

Want to help? Pick any open item from the current Phase and comment on an issue (we'll create them soon).

---

**Let's build the most useful WhatsApp tool ever made for Indian farmers.**

— Life2death
