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

- **2026-04-17 — Module 1: WhatsApp Cloud API Wrapper**
 - Chose: `pywa` v4.0.0
 - Runner-up: `heyoo`
 - Why: Production-stable, BSUID-migration ready, async-first, minimal dependencies (httpx only), active maintenance (Feb 2026), FastAPI integration
 - Trade-off accepted: Slightly more complex API than heyoo, but higher reliability for production and future Meta changes
 - Evaluation: `vendor-research/01-whatsapp-wrapper.md`
 - Marathi requirement: Noted. Templates, message text, and captions support UTF-8 Marathi natively. Transliteration module (Module 9) will handle Hinglish↔Marathi conversion