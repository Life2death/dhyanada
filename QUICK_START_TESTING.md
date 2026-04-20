# Quick Start: Test Kisan AI in 30 Minutes

## The Fastest Way to Test Your App

### Option A: Test Locally (5 minutes)

```bash
# 1. Start the server
cd /c/Users/vikra/projects/dhanyada
uvicorn src.main:app --reload

# 2. Test admin dashboard
http://localhost:8000/admin/
Login: admin / changeme

# 3. Test farmer dashboard
http://localhost:8000/farmer/login
Phone: +919876543210
```

✅ **All works locally? Ready to deploy!**

---

### Option B: Deploy Free to Railway (30 minutes) ⭐ RECOMMENDED

**Step 1: Prepare (2 min)**
```bash
# Make sure all code is committed
git add -A
git commit -m "Ready for Railway deployment"
git push origin main
```

**Step 2: Sign Up (2 min)**
```
1. Visit https://railway.app
2. Click "Sign in with GitHub"
3. Grant access
```

**Step 3: Create Project (3 min)**
```
1. Click "New Project"
2. Select "GitHub Repo"
3. Choose dhanyada
4. Select main branch
```

**Step 4: Add Databases (6 min)**
```
1. Click "Add Service" → PostgreSQL → Add
2. Click "Add Service" → Redis → Add
3. Wait for both to start
```

**Step 5: Add Docker App (3 min)**
```
1. Click "Add Service" → GitHub Repo
2. Select dhanyada repository
3. Railway detects Dockerfile ✅
```

**Step 6: Set Environment Variables (7 min)**
```
Click Docker service → Variables → Raw Editor → Paste:

FASTAPI_ENV=production
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.DATABASE_URL}}

WHATSAPP_PHONE_ID=1135216599663873
WHATSAPP_TOKEN=your_token_here
WHATSAPP_BUSINESS_ACCOUNT_ID=1888194241890478
WHATSAPP_VERIFY_TOKEN=webhook_token

ADMIN_USERNAME=admin
ADMIN_PASSWORD=testpass123
JWT_SECRET=your_secret_key_32_chars_min

OPENWEATHER_API_KEY=your_openweather_api_key_here
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ADMIN_EMAIL=your_email@gmail.com

CALLBACK_URL=${{Railway.PUBLIC_DOMAIN}}/webhook/whatsapp
```

**Step 7: Deploy (5 min)**
```
1. Click "Deploy"
2. Watch logs
3. Wait for "Application startup complete"
```

**Step 8: Test (2 min)**
```
Click "Public Domain" → Test URLs:
  ✅ https://your-project-xxx.railway.app/health
  ✅ https://your-project-xxx.railway.app/admin/
  ✅ https://your-project-xxx.railway.app/farmer/login
```

✅ **Live on internet in 30 minutes!**

---

## What You Can Test

### ✅ Admin Dashboard
**URL:** https://your-app.railway.app/admin/
**Login:** admin / testpass123

Features to test:
- [ ] Overview tab (DAU, messages, crops)
- [ ] System Health (service status)
- [ ] Error Logs (track errors)
- [ ] Real-time refresh

### ✅ Farmer Dashboard
**URL:** https://your-app.railway.app/farmer/login

Features to test:
- [ ] OTP request
- [ ] OTP verification
- [ ] Price tracking (30-day history)
- [ ] Weather forecasts
- [ ] Government schemes
- [ ] Activity metrics

### ✅ WhatsApp Bot
**Send message:** "weather pune" to bot number
**Expected response:** Within 5 seconds with weather data

### ✅ Health Check
**URL:** https://your-app.railway.app/health
**Expected:** 200 OK with service statuses

---

## Testing Checklist

### Before Deployment
- [ ] Code committed to main branch
- [ ] .env.example file exists
- [ ] Dockerfile present
- [ ] All tests pass locally (pytest)

### After Deployment
- [ ] Health endpoint returns 200
- [ ] Admin dashboard loads
- [ ] Farmer login page shows
- [ ] Database migrations ran successfully
- [ ] Error logs visible
- [ ] WhatsApp webhook accepts POST
- [ ] No errors in deployment logs

### Feature Testing
- [ ] Admin can login
- [ ] Admin can view metrics
- [ ] Farmer can request OTP
- [ ] Farmer can verify OTP
- [ ] Farmer dashboard loads data
- [ ] Prices show for farmer's crops
- [ ] Weather shows for farmer's district
- [ ] Schemes filtered correctly
- [ ] Auto-refresh works
- [ ] Mobile responsive design works

---

## Cost Summary

| Option | Cost | Time | Best For |
|--------|------|------|----------|
| Local Testing | $0 | 5 min | Quick testing |
| Railway.app | FREE | 30 min | Demo/testing |
| DigitalOcean | $15/mo | 45 min | Staging |
| Production | $25/mo | 1 hour | Live deployment |

---

## Free Tier Limits (Railway)

- **CPU:** Shared (sufficient for testing)
- **Memory:** Up to 2GB
- **Storage:** 5GB total
- **Databases:** Unlimited (within 5GB)
- **Credit:** $5/month (replenishing)
- **Projects:** 5 maximum
- **Auto-deploy:** Yes (via GitHub)

---

## Common Testing Scenarios

### Scenario 1: Admin Monitoring
```
1. Deploy to Railway
2. Visit /admin/
3. See real-time metrics
4. Check error tracking
5. Monitor service health
```
**Time:** 5 min

### Scenario 2: Farmer Experience
```
1. Deploy to Railway
2. Visit /farmer/login
3. Request OTP
4. Verify with test OTP
5. View dashboard
6. Check prices/weather/schemes
```
**Time:** 10 min

### Scenario 3: WhatsApp Integration
```
1. Deploy to Railway
2. Send WhatsApp message to bot
3. Check response
4. View logs in admin
5. Verify error handling
```
**Time:** 5 min

---

## Troubleshooting Quick Guide

| Issue | Solution |
|-------|----------|
| Deploy fails | Check Python version in Dockerfile (3.11) |
| Database error | Ensure DATABASE_URL = ${{Postgres.DATABASE_URL}} |
| WhatsApp not working | Check CALLBACK_URL and webhook token in Meta |
| Out of memory | Reduce batch sizes, add more RAM |
| Static files missing | Don't worry, HTML is embedded in Python |
| No data showing | Check if farmer crops/weather data exists |

---

## After Testing: Next Steps

### If Testing on Railway Works ✅
```
→ Deploy to DigitalOcean for staging
→ Set up custom domain
→ Enable SSL
→ Test with real farmers
→ Collect feedback
```

### If Testing Shows Issues ❌
```
→ Check logs in Railway dashboard
→ Fix bugs locally
→ Push to GitHub
→ Railway auto-redeploys
→ Test again
```

---

## Get Support

### Documentation
- [PROJECT_STATUS_REPORT.md](./PROJECT_STATUS_REPORT.md) — Full status
- [DEPLOYMENT_OPTIONS_COMPARISON.md](./DEPLOYMENT_OPTIONS_COMPARISON.md) — Detailed options
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Production guide
- [PRODUCTION_CHECKLIST.md](./PRODUCTION_CHECKLIST.md) — Pre-launch checklist

### Quick Links
- Railway: https://railway.app
- DigitalOcean: https://www.digitalocean.com
- GitHub: https://github.com
- Meta WhatsApp: https://developers.facebook.com/whatsapp

---

## Summary

**You have 2 options:**

### 1️⃣ Test Locally (5 min)
```bash
uvicorn src.main:app --reload
http://localhost:8000/admin/
```

### 2️⃣ Deploy Free (30 min)
```
Sign up → Railway.app
Push code → GitHub
Click Deploy → Done!
Visit URL → Test live
```

**Recommendation:** Do BOTH!
- Test locally first (find bugs quickly)
- Deploy to Railway (show stakeholders)

---

## Expected Results

After successful deployment, you'll have:

✅ Live WhatsApp bot (receives messages)
✅ Admin dashboard (monitoring)
✅ Farmer portal (personalized data)
✅ Error tracking (alerting)
✅ Production-grade infrastructure
✅ Auto-scaling capability
✅ 99.5% uptime SLA

All working at **zero cost** (Railway free tier)!

---

**Ready to deploy?** → Choose Option A or B above and start! 🚀

**Questions?** → Check the detailed docs linked above.

**Have bugs?** → Fix locally, push to GitHub, Railway auto-redeploys.

**Want more features?** → Phase 4 Step 2 (multi-language) ready to implement!
