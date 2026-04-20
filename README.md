# Dhanyada — Giver of Grains 🌾

**A WhatsApp-based farming bot for Maharashtra farmers** providing real-time market prices, government scheme eligibility, pest diagnosis, and alert subscriptions.

**Status**: ✅ Phase 2 Complete (Production-Ready) | ⏳ Phase 3 In Progress (Testing + Dashboard)

---

## Quick Start

### Requirements
- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- WhatsApp Business Account (Meta)

### Installation

```bash
# Clone & install
git clone https://github.com/your-org/dhanyada
cd dhanyada
pip install -r requirements.txt

# Setup database
alembic upgrade head

# Run server (Terminal 1)
uvicorn src.main:app --reload

# Run Celery worker (Terminal 2)
celery -A src.scheduler.celery_app worker -l info

# Run Celery Beat (Terminal 3)
celery -A src.scheduler.celery_app beat -l info
```

### Environment Variables
See `.env.example` or `IMPLEMENTATION_GUIDE.md` for complete list.

---

## Architecture

```
┌─────────────────────────────────┐
│    WhatsApp Meta API            │
└──────────────┬──────────────────┘
               │
┌──────────────v──────────────────┐
│  FastAPI Webhook Handler        │
│  (/webhook/whatsapp)            │
└──────────────┬──────────────────┘
               │
┌──────────────v──────────────────┐
│  Intent Classification           │
│  ├─ Regex (85%, instant)        │
│  └─ LLM fallback (Gemini)       │
└──────────────┬──────────────────┘
               │
       ┌───────┴───────┐
       │               │
    Handlers       Scheduler (Celery Beat)
       │               │
    ├─ Price          ├─ Ingest Prices (8 PM)
    ├─ Scheme         ├─ Trigger Alerts (8:30 PM)
    ├─ Weather        ├─ Ingest Schemes (6:15 AM)
    ├─ Pest           ├─ Trigger MSP (6:20 AM)
    └─ Alert          └─ Broadcast (6:30 AM)
       │
       └──→ PostgreSQL Database
```

---

## Features (Phase 2 - Complete ✅)

### Module 1: Price Queries
Query real-time mandi (market) prices from 4 sources:
- Agmarknet API (Government of India)
- MSIB Scraper
- NHRDF Onion Prices
- Vashi APMC

**Example**: "कांदा किंमत?" (What's the onion price?)

### Module 2: Weather Forecasts
5-day weather forecast for 5 districts (IMD + OpenWeather):

**Example**: "पुणे हवामान?" (Weather in Pune?)

### Module 3: Pest Diagnosis
AI-powered crop disease detection via image upload:
- TensorFlow model (local)
- Google Gemini Vision API (detailed analysis)

**Example**: Upload crop image → diagnosis

### Module 4: Government Schemes
Check eligibility for schemes:
- PM-KISAN (₹6,000/year)
- PM-FASAL (Crop insurance)
- Rashtriya Kranti (Soil health)
- State schemes

Eligibility based on: age, land size, crops

**Example**: "मला कोणती योजना मिळेल?" (What schemes am I eligible for?)

### Module 5: Price Alerts
Set mandi price alerts with conditions:

**Example**: "कांदा ₹4000 से अधिक सूचित करो" (Alert when onion > ₹4000)

---

## Test Coverage (Phase 3 - Validated ✅)

```
✅ 129/134 tests passing (96% success rate)

test_threshold_parser:       34/34 ✅
test_farmer_service:         13/13 ✅
test_regex_classifier:       45/45 ✅
test_scheduler_tasks:        10/10 ✅ (5 skipped - test env only)
test_intent_routing:         27/27 ✅
```

**Run tests**:
```bash
pytest src/tests/test_threshold_parser.py \
        src/tests/test_farmer_service.py \
        src/tests/test_regex_classifier_phase2.py \
        src/tests/test_scheduler_tasks.py \
        src/tests/test_intent_routing.py -v
```

---

## Documentation

- **IMPLEMENTATION_GUIDE.md** - Complete setup, architecture, API reference
- **PHASE3_PROGRESS.md** - Current phase status and roadmap
- **SESSION2_COMPLETION_SUMMARY.md** - Phase 2 deliverables and metrics

---

## Development Workflow

### 1. Create a feature branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make changes and test
```bash
pytest src/tests/ -v
```

### 3. Commit with descriptive message
```bash
git commit -m "Brief description of changes"
```

### 4. Push and create pull request
```bash
git push origin feature/your-feature-name
```

---

## Production Deployment (Phase 3 In Progress)

### Current Status
- ✅ Phase 2 infrastructure validated (129 tests)
- ⏳ Admin dashboard (in development)
- ⏳ Monitoring & alerting (queued)
- ⏳ Deployment playbook (queued)

### Pre-Deployment Checklist
- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL certificate installed
- [ ] Redis running
- [ ] Celery worker configured
- [ ] Monitoring setup complete

See `PHASE3_PROGRESS.md` for deployment timeline.

---

## Performance Targets

| Operation | Target | Status |
|-----------|--------|--------|
| Regex classification | < 10ms | ✅ Met |
| LLM classification | < 2s | ✅ Met |
| Price query | < 500ms | ✅ Cached |
| Scheme query | < 1s | ✅ Met |
| WhatsApp response | < 5s total | ✅ Target |

---

## Support & Troubleshooting

### Common Issues

**"Database connection refused"**
```bash
# Check PostgreSQL is running
psql -U postgres -d dhanyada -c "SELECT 1"
```

**"Celery task not running"**
```bash
# Check Redis is running
redis-cli ping  # Should return PONG

# Check Celery worker
celery -A src.scheduler.celery_app inspect active
```

**"WhatsApp webhook not receiving messages"**
- Verify webhook URL is public (ngrok for local dev)
- Check verify token matches environment variable
- Ensure FastAPI is running on correct port

### Get Logs
```bash
# View recent logs
tail -f /var/log/dhanyada/app.log

# Search for errors
grep "ERROR" /var/log/dhanyada/app.log
```

---

## Technology Stack

- **Framework**: FastAPI (async Python)
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL 13+
- **ORM**: SQLAlchemy with async support
- **API**: WhatsApp Meta Business API
- **ML**: TensorFlow + Google Gemini Vision
- **Testing**: pytest with pytest-asyncio
- **Deployment**: Docker + Kubernetes (planned)

---

## Roadmap (Phase 3-4)

### Phase 3: Production Validation ✅ In Progress
- ✅ Test suite validation (129 tests)
- ⏳ Admin dashboard
- ⏳ Monitoring setup
- ⏳ Deployment playbook

### Phase 4: Launch & Scale (May 2026+)
- Multi-state expansion (TN, KA, UP)
- Video pest diagnosis
- Loan/credit eligibility
- Supply chain integration

---

## Contributing

1. Read `CONTRIBUTING.md` (if exists)
2. Follow code style: `black`, `isort`, `flake8`
3. Write tests for new features
4. Update documentation
5. Submit PR with clear description

---

## License

Proprietary - Kisan AI Foundation

---

## Contact

- **Support**: support@dhanyada.com
- **Issues**: GitHub Issues
- **Team**: [Team members]

---

**Made with ❤️ for Maharashtra farmers**  
*Last Updated: 2026-04-18*
