# Quick Test Commands - Copy & Paste Reference

**Keep this open in another terminal while developing**

---

## 🚀 EVERYDAY COMMANDS

### Before Making a Commit
```bash
# 1. Run unit tests (fast - 5 seconds)
pytest src/tests/test_threshold_parser.py \
        src/tests/test_farmer_service.py \
        src/tests/test_regex_classifier_phase2.py \
        src/tests/test_intent_routing.py -v

# Expected: ✅ 119 passed in ~3 seconds
```

### Before Pushing to GitHub
```bash
# 1. Run ALL tests including integration
pytest src/tests/ -v

# Expected: ✅ 129 passed, 5 skipped in ~5 seconds

# 2. Generate coverage report
pytest src/tests/ --cov=src --cov-report=html

# View: open htmlcov/index.html
```

---

## 📋 SPECIFIC MODULE TESTS

### Test Price Threshold Parser
```bash
pytest src/tests/test_threshold_parser.py -v
# Tests: "₹5000", "5,000", "1,00,000", "5000/quintal"
```

### Test Farmer Service
```bash
pytest src/tests/test_farmer_service.py -v
# Tests: farmer lookup, crops, subscriptions
```

### Test Intent Classifier
```bash
pytest src/tests/test_regex_classifier_phase2.py -v
# Tests: intent detection for all Phase 2 modules
```

### Test Intent Routing
```bash
pytest src/tests/test_intent_routing.py -v
# Tests: intent-to-handler mapping for all 13 intents
```

### Test Scheduler Tasks
```bash
# ⚠️ Requires PostgreSQL + Redis running first
pytest src/tests/test_scheduler_tasks.py -v
# Tests: alert triggering, ingestion summaries
```

---

## 🎯 SINGLE TEST EXECUTION

### Run One Specific Test
```bash
# Example: Test extracting ₹5000
pytest src/tests/test_threshold_parser.py::TestExtractPriceValue::test_rupee_symbol_no_comma -v

# Example: Test farmer lookup
pytest src/tests/test_farmer_service.py::TestFarmerServiceGetByPhone::test_get_existing_farmer -v

# Example: Test PRICE_ALERT detection
pytest src/tests/test_regex_classifier_phase2.py::TestPriceAlertPatterns::test_alert_keyword_english -v
```

---

## 📊 ANALYSIS & REPORTS

### Show Which Tests Are Slowest
```bash
pytest src/tests/ -v --durations=10
```

### Show Coverage by Module
```bash
pytest src/tests/ --cov=src --cov-report=term-missing
```

### Generate HTML Report
```bash
pytest src/tests/ --html=report.html --self-contained-html
open report.html
```

### Run Only Tests That Failed Last Time
```bash
pytest src/tests/ --lf
```

### Stop at First Failure (for debugging)
```bash
pytest src/tests/ -x
```

---

## ⚙️ ENVIRONMENT SETUP

### First Time Setup
```bash
# 1. Install test dependencies
pip install -r requirements.txt

# 2. Check Python version (must be 3.9+)
python --version

# 3. Verify test file paths
ls -la src/tests/test_*.py

# 4. Run a quick test to verify setup
pytest src/tests/test_threshold_parser.py::TestExtractCondition::test_greater_than_symbol -v
```

### Fix Common Issues
```bash
# Issue: "pytest not found"
pip install pytest pytest-asyncio

# Issue: "ModuleNotFoundError: No module named 'src'"
# Make sure you're in /c/Users/vikra/projects/dhanyada directory
cd /c/Users/vikra/projects/dhanyada
pwd  # Verify you're in dhanyada folder

# Issue: "Database connection refused"
# PostgreSQL required for some tests
# Tests will skip automatically if DB not available
redis-cli ping  # Check Redis (should show PONG)
```

---

## 🔥 FULL SYSTEM TEST (End-to-End)

### Start All Services
```bash
# Terminal 1: PostgreSQL & create DB
createdb dhanyada
alembic upgrade head

# Terminal 2: Redis
redis-server

# Terminal 3: FastAPI
uvicorn src.main:app --reload

# Terminal 4: Celery Worker
celery -A src.scheduler.celery_app worker -l info

# Terminal 5: Celery Beat Scheduler
celery -A src.scheduler.celery_app beat -l info

# Terminal 6: Run manual tests
# See TESTING_PLAYBOOK.md for test requests
```

---

## 🎓 LEARNING FLOW

### 1️⃣ Start Here - Understand Thresholds
```bash
# Read: src/tests/test_threshold_parser.py (simple, fast)
# Run: pytest src/tests/test_threshold_parser.py -v
# Time: 5 minutes
```

### 2️⃣ Then - Understand Intents
```bash
# Read: src/tests/test_intent_routing.py (straightforward)
# Run: pytest src/tests/test_intent_routing.py -v
# Time: 5 minutes
```

### 3️⃣ Then - Understand Classifier
```bash
# Read: src/tests/test_regex_classifier_phase2.py (detailed)
# Run: pytest src/tests/test_regex_classifier_phase2.py -v
# Time: 10 minutes
```

### 4️⃣ Finally - Advanced (Async + Database)
```bash
# Read: src/tests/test_farmer_service.py (async patterns)
# Read: src/tests/test_scheduler_tasks.py (integration)
# Run: pytest src/tests/ -v
# Time: 15 minutes
```

---

## 💡 PRO TIPS

### Tip 1: Watch Tests Continuously During Development
```bash
# Install pytest-watch
pip install pytest-watch

# Watch mode - reruns tests on file changes
ptw src/tests/
# Now edit code, tests auto-run!
```

### Tip 2: Run Tests in Parallel (Faster)
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run with 4 workers
pytest src/tests/ -n 4
```

### Tip 3: Debug Failing Test with Print Statements
```bash
# Add this to test:
import pdb; pdb.set_trace()

# Run with:
pytest src/tests/test_file.py -s  # -s = show print output
```

### Tip 4: Keep Test Output Simple
```bash
# Quiet mode - only show summary
pytest src/tests/ -q

# Only show failures
pytest src/tests/ --tb=short
```

---

## ✅ CHECKLIST BEFORE PRODUCTION

```bash
# ✅ 1. Run all tests
pytest src/tests/ -v

# ✅ 2. Check coverage (should be > 80%)
pytest src/tests/ --cov=src --cov-report=term

# ✅ 3. No security vulnerabilities
pip install safety
safety check

# ✅ 4. Code quality
pip install black flake8
black --check src/
flake8 src/

# ✅ 5. Database migrations work
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# ✅ 6. All environment variables set
echo $DATABASE_URL
echo $REDIS_URL
echo $WHATSAPP_TOKEN

# ✅ 7. System starts without errors
uvicorn src.main:app --host 0.0.0.0 --port 8000

# 🚀 READY FOR PRODUCTION!
```

---

## 📞 HELP

### Still having issues? Check:
1. **TESTING_PLAYBOOK.md** - Comprehensive guide
2. **pytest --help** - Official pytest help
3. **Python error message** - Google the exact error

### Quick Diagnostics
```bash
# Check setup
python --version              # Should be 3.9+
pytest --version             # Should be 7.0+
python -c "import sqlalchemy; print(sqlalchemy.__version__)"

# Check if tests are discoverable
pytest src/tests/ --collect-only -q

# Run with maximum verbosity
pytest src/tests/ -vvv --tb=long
```

---

**Last Updated**: 2026-04-18  
**All Tests Passing**: ✅ 129/134  
**Status**: Ready for Production
