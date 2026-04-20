# Production Deployment Checklist — Dhanyada

Complete this checklist before deploying to production.

---

## Pre-Deployment (Development Environment)

### Code Quality

- [ ] **All tests pass locally**
  ```bash
  pytest src/tests/ -v
  # Expected: 130+ tests passing
  ```

- [ ] **Code meets style standards**
  ```bash
  black --check src/
  isort --check-only src/
  flake8 src/ --max-line-length=120
  ```

- [ ] **No hardcoded secrets in code**
  - [ ] No API keys in src/config.py
  - [ ] No passwords in models
  - [ ] No tokens in handlers
  ```bash
  # Search for common secrets
  grep -r "sk_" src/  # OpenAI keys
  grep -r "password" src/ --exclude-dir=migrations
  grep -r "secret" src/config.py
  ```

- [ ] **Coverage >= 80%**
  ```bash
  pytest src/tests/ --cov=src --cov-report=term-missing
  # Expected: 80%+ coverage
  ```

- [ ] **No TODO/FIXME in production code**
  ```bash
  grep -r "TODO\|FIXME" src/ --exclude-dir=migrations
  # All items addressed or moved to GitHub issues
  ```

### Docker Image

- [ ] **Docker image builds successfully**
  ```bash
  docker build -t dhanyada:latest .
  # No errors, warnings reviewed
  ```

- [ ] **Image size is optimized**
  ```bash
  docker image ls dhanyada
  # Expected: ~200MB (multi-stage build)
  # Alert if > 400MB
  ```

- [ ] **Image runs locally**
  ```bash
  docker run -p 8000:8000 \
    -e DATABASE_URL="sqlite:///./test.db" \
    -e REDIS_URL="redis://redis:6379" \
    dhanyada:latest
  curl http://localhost:8000/health
  # Expected: 200 OK response
  ```

- [ ] **Non-root user inside container**
  ```bash
  docker run dhanyada:latest id
  # Expected: uid=1000 (appuser), not uid=0 (root)
  ```

- [ ] **Health check endpoint works**
  ```bash
  docker run -p 8000:8000 dhanyada:latest &
  sleep 5
  curl http://localhost:8000/health
  # Expected: {"status": "ok", "services": {...}}
  ```

### Docker Compose (Full Stack)

- [ ] **All services start without errors**
  ```bash
  docker-compose up -d
  docker-compose ps
  # Expected: postgres, redis, app, worker, beat all healthy/running
  ```

- [ ] **PostgreSQL service is healthy**
  ```bash
  docker-compose exec postgres pg_isready-U dhanyada
  # Expected: accepting connections
  ```

- [ ] **Redis service is healthy**
  ```bash
  docker-compose exec redis redis-cli ping
  # Expected: PONG
  ```

- [ ] **FastAPI app is healthy**
  ```bash
  curl http://localhost:8000/health
  # Expected: 200 OK with service statuses
  ```

- [ ] **Database migrations run automatically**
  ```bash
  docker-compose logs app | grep "alembic"
  # Expected: see migration messages
  docker-compose exec app alembic current
  # Expected: latest version number
  ```

- [ ] **Admin dashboard is accessible**
  ```bash
  curl http://localhost:8000/admin/
  # Expected: HTML response, 200 OK
  curl -H "Cookie: access_token=invalid" http://localhost:8000/admin/
  # Expected: 401 Unauthorized (auth working)
  ```

- [ ] **WhatsApp webhook is callable**
  ```bash
  curl -X GET "http://localhost:8000/webhook/whatsapp?hub.challenge=test"
  # Expected: 400 or error (missing verify token)
  curl -X GET "http://localhost:8000/webhook/whatsapp?hub.challenge=test&hub.verify_token=test"
  # Expected: different response (token logic working)
  ```

- [ ] **Celery worker can process tasks**
  ```bash
  # Check worker logs
  docker-compose logs worker | tail -20
  # Expected: "Ready to accept tasks" message
  ```

- [ ] **Celery beat scheduler is running**
  ```bash
  docker-compose logs beat | tail -20
  # Expected: "Scheduler: Sending due task..." messages
  ```

### Configuration

- [ ] **Environment variables configured**
  ```bash
  # Check .env file exists
  ls -la .env
  # Verify all required vars are set
  ```

- [ ] **No .env file in Git**
  ```bash
  git status | grep .env
  # Expected: no output (file ignored)
  cat .gitignore | grep .env
  # Expected: .env present in .gitignore
  ```

- [ ] **Sensitive vars are not logged**
  ```bash
  docker-compose logs app | grep -i "token\|password\|secret"
  # Expected: no actual secrets printed (just placeholders)
  ```

- [ ] **JWT secret is unique**
  ```bash
  grep "JWT_SECRET" .env
  # Expected: NOT "your-secret-key-change-in-production"
  # Should be 32+ character random string
  ```

- [ ] **Admin password is changed**
  ```bash
  grep "ADMIN_PASSWORD" .env
  # Expected: NOT "changeme"
  ```

---

## Production Environment Setup

### Infrastructure

- [ ] **VPS or cloud server provisioned**
  - [ ] Ubuntu 22.04 LTS (or similar)
  - [ ] 2GB+ RAM
  - [ ] 50GB+ SSD storage
  - [ ] Firewall configured (80, 443, 22)

- [ ] **Domain name acquired and configured**
  ```bash
  nslookup your-domain.com
  # Expected: resolves to server IP
  ```

- [ ] **DNS TTL lowered to 300s** (for migrations)
  ```bash
  # In your domain registrar, set TTL to 300 seconds
  ```

- [ ] **Docker and docker-compose installed**
  ```bash
  ssh ubuntu@your-server-ip
  docker --version
  docker-compose --version
  # Expected: docker 24+, compose 2.20+
  ```

- [ ] **Firewall rules configured**
  ```bash
  sudo ufw status
  # Expected: SSH (22), HTTP (80), HTTPS (443) allowed
  ```

- [ ] **SSH keys configured** (no password auth)
  ```bash
  cat /etc/ssh/sshd_config | grep PasswordAuthentication
  # Expected: no (password auth disabled)
  ```

### Database Setup

- [ ] **PostgreSQL database created**
  ```bash
  docker-compose exec postgres psql -U dhanyada -d dhanyada -c "SELECT version();"
  # Expected: PostgreSQL 16 version string
  ```

- [ ] **Database user has correct permissions**
  ```bash
  docker-compose exec postgres psql -U dhanyada -d dhanyada -c "GRANT ALL ON SCHEMA public TO dhanyada;"
  ```

- [ ] **Migrations have run**
  ```bash
  docker-compose exec app alembic current
  # Expected: version number like "1234567890abc_version_name"
  ```

- [ ] **Tables created successfully**
  ```bash
  docker-compose exec postgres psql -U dhanyada -d dhanyada -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';"
  # Expected: number > 5 (multiple tables created)
  ```

- [ ] **Backup script created and tested**
  ```bash
  sudo /app/backup.sh
  ls -la /backups/dhanyada/
  # Expected: recent dump file
  ```

- [ ] **Automated daily backups configured**
  ```bash
  sudo crontab -l | grep backup
  # Expected: backup.sh scheduled daily
  ```

### SSL/HTTPS

- [ ] **SSL certificate obtained**
  ```bash
  sudo ls -la /etc/letsencrypt/live/your-domain.com/
  # Expected: fullchain.pem, privkey.pem exist
  ```

- [ ] **Certificate auto-renewal configured**
  ```bash
  sudo certbot renew --dry-run
  # Expected: success message
  ```

- [ ] **Nginx reverse proxy configured**
  ```bash
  sudo nginx -t
  # Expected: "test successful"
  ```

- [ ] **HTTPS redirects HTTP traffic**
  ```bash
  curl http://your-domain.com -L
  # Expected: redirects to https://
  ```

- [ ] **SSL certificate is valid**
  ```bash
  openssl s_client -connect your-domain.com:443 < /dev/null | grep -A2 "subject="
  # Expected: certificate name matches domain
  ```

- [ ] **Security headers are present**
  ```bash
  curl -I https://your-domain.com
  # Expected: Strict-Transport-Security, X-Content-Type-Options, X-Frame-Options
  ```

### Email Configuration

- [ ] **SMTP credentials are correct**
  ```bash
  # Test SMTP connection manually or via logs
  docker-compose logs app | grep -i "smtp\|email"
  # Expected: no connection errors
  ```

- [ ] **Admin email is set**
  ```bash
  grep "ADMIN_EMAIL" .env
  # Expected: valid email address
  ```

- [ ] **Test alert email sent successfully**
  - [ ] Trigger an alert (e.g., invalid request) from admin dashboard
  - [ ] Check admin email for alert notification
  - [ ] Expected: email received within 1 minute

- [ ] **Email is not marked as spam**
  - [ ] Check spam/promotions folders
  - [ ] Add sender to contacts if needed

### WhatsApp Configuration

- [ ] **Phone ID is correct**
  ```bash
  grep "WHATSAPP_PHONE_ID" .env
  # Should match Meta App Dashboard
  ```

- [ ] **Access token is valid**
  ```bash
  curl -X GET "https://graph.instagram.com/me?access_token=${WHATSAPP_TOKEN}"
  # Expected: 200 OK (not 401 Unauthorized)
  ```

- [ ] **Webhook URL updated in Meta Dashboard**
  - [ ] Go to Meta App Dashboard
  - [ ] WhatsApp → Configuration
  - [ ] Webhook URL: `https://your-domain.com/webhook/whatsapp`
  - [ ] Verify Token: (matches `WHATSAPP_VERIFY_TOKEN` in .env)

- [ ] **Webhook verification test passed**
  ```bash
  curl -X GET "https://your-domain.com/webhook/whatsapp?hub.mode=subscribe&hub.challenge=test123&hub.verify_token=your_verify_token"
  # Expected: returns "test123"
  ```

- [ ] **Subscribe to WhatsApp messages**
  - [ ] In Meta Dashboard, subscribe to messages webhook
  - [ ] Expected: subscription confirmed

### API Keys

- [ ] **OpenWeather API key is valid**
  ```bash
  curl "https://api.openweathermap.org/data/2.5/weather?q=Pune&appid=${OPENWEATHER_API_KEY}"
  # Expected: 200 OK with weather data
  ```

- [ ] **AgroMonitoring API key is valid** (if using)
  ```bash
  curl "https://api.agromonitoring.com/agro/1.0/accounts/status?appid=${AGROMONITORING_API_KEY}"
  # Expected: 200 OK
  ```

- [ ] **All API keys have rate limits checked**
  - [ ] OpenWeather: >= 1000 calls/day
  - [ ] AgroMonitoring: >= 500 calls/day
  - [ ] Agmarknet: as needed

---

## Application Testing

### Functional Testing

- [ ] **Health check returns 200 OK**
  ```bash
  curl https://your-domain.com/health
  # Expected: {"status": "ok", "services": {"postgres": "ok", ...}}
  ```

- [ ] **Admin dashboard loads**
  ```bash
  # Visit: https://your-domain.com/admin/
  # Expected: login page appears (not 404, not blank)
  ```

- [ ] **Admin dashboard login works**
  - [ ] Username: (from ADMIN_USERNAME)
  - [ ] Password: (from ADMIN_PASSWORD)
  - [ ] Expected: dashboard appears after login

- [ ] **Dashboard tabs load data**
  - [ ] Overview tab: shows user metrics
  - [ ] System Health: shows service status
  - [ ] Error Logs: shows recent errors
  - [ ] All without JavaScript errors

- [ ] **WhatsApp webhook receives messages**
  - [ ] Send test message on WhatsApp to bot number
  - [ ] Expected: message logged in app
  - [ ] Check logs: `docker-compose logs app | grep -i "whatsapp\|received"`

- [ ] **Bot replies to messages**
  - [ ] Send: "weather pune"
  - [ ] Expected: weather response within 5 seconds
  - [ ] Check logs for weather API call

- [ ] **Weather data is fresh**
  - [ ] Ask bot: "weather in <city>"
  - [ ] Verify response matches current conditions
  - [ ] Expected: timestamp is recent (not cached old data)

- [ ] **Error handling works**
  - [ ] Send invalid input to bot
  - [ ] Expected: graceful error message (not crash)
  - [ ] Check error logs in dashboard

- [ ] **Database stores messages**
  ```bash
  docker-compose exec postgres psql -U dhanyada -d dhanyada \
    -c "SELECT COUNT(*) FROM message_table;"
  # Expected: number > 0 (messages recorded)
  ```

### Performance Testing

- [ ] **Response time < 2 seconds**
  ```bash
  for i in {1..10}; do
    curl -w "Time: %{time_total}s\n" https://your-domain.com/health
  done
  # Expected: all < 2 seconds
  ```

- [ ] **Concurrent requests handled**
  ```bash
  ab -n 100 -c 10 https://your-domain.com/health
  # Expected: most requests succeed (may have some failures under stress)
  ```

- [ ] **Database query performance is acceptable**
  ```bash
  docker-compose exec postgres psql -U dhanyada -d dhanyada \
    -c "SELECT COUNT(*) FROM error_log; SELECT COUNT(*) FROM message_table;"
  # Expected: queries complete quickly (< 1 second)
  ```

- [ ] **Background tasks process within SLA**
  - [ ] Send weather request (background task)
  - [ ] Check logs: task queued → processing → completed
  - [ ] Expected: total time < 10 seconds

- [ ] **Celery worker queue is not backlogged**
  ```bash
  docker-compose exec redis redis-cli LLEN celery
  # Expected: 0 or small number (not hundreds)
  ```

### Security Testing

- [ ] **SQL injection is blocked**
  ```bash
  curl "https://your-domain.com/api/something?q=test' OR '1'='1"
  # Expected: error or no data leakage
  ```

- [ ] **XSS attacks are prevented**
  - [ ] Admin dashboard sanitizes error messages
  - [ ] Expected: error message displayed as text, not HTML

- [ ] **CSRF protection enabled**
  ```bash
  curl -X POST https://your-domain.com/api/admin \
    -d '{"action": "delete"}'
  # Expected: 403 Forbidden or CSRF token required
  ```

- [ ] **No sensitive info in error responses**
  ```bash
  curl https://your-domain.com/nonexistent
  # Expected: generic error, no stacktrace, no file paths
  ```

- [ ] **Environment variables not exposed**
  ```bash
  curl https://your-domain.com/debug
  # Expected: 404 Not Found (no debug endpoint)
  ```

- [ ] **Database credentials not in logs**
  ```bash
  docker-compose logs app | grep "postgresql://\|password="
  # Expected: no output (no exposed creds)
  ```

- [ ] **API requests use HTTPS only**
  ```bash
  # All requests should redirect HTTP to HTTPS
  curl http://your-domain.com -I
  # Expected: 301 redirect to https://
  ```

---

## Monitoring & Logging

### Logs are being captured

- [ ] **Application logs are present**
  ```bash
  docker-compose logs app | wc -l
  # Expected: many lines of logs
  ```

- [ ] **Error logs are persisted**
  ```bash
  docker-compose exec postgres psql -U dhanyada -d dhanyada \
    -c "SELECT COUNT(*) FROM error_log;"
  # Expected: > 0 (errors captured)
  ```

- [ ] **Service health is being tracked**
  ```bash
  docker-compose exec postgres psql -U dhanyada -d dhanyada \
    -c "SELECT * FROM service_health LIMIT 1;"
  # Expected: service health record
  ```

- [ ] **Logs are rotated** (not growing indefinitely)
  ```bash
  du -sh /var/lib/docker/containers/*/
  # Expected: under 500MB total
  ```

### Alerting is configured

- [ ] **Email alerts can be sent**
  - [ ] Trigger a high-error-rate scenario
  - [ ] Check admin email for alert
  - [ ] Expected: alert email received

- [ ] **Alert deduplication works**
  - [ ] Trigger same error multiple times
  - [ ] Expected: only one alert email (not spam)

- [ ] **Health check alerts work**
  - [ ] Stop a service temporarily
  - [ ] Expected: alert email sent
  - [ ] Restart service
  - [ ] Expected: recovery email (if configured)

---

## Documentation

- [ ] **DEPLOYMENT.md exists and is accurate**
  - [ ] VPS setup steps work
  - [ ] Environment variable instructions are clear
  - [ ] Troubleshooting section covers common issues

- [ ] **PRODUCTION_CHECKLIST.md is complete** (this file)
  - [ ] All items applicable to your setup
  - [ ] Adjust/remove items if needed

- [ ] **README.md has updated deploy section**
  - [ ] Links to DEPLOYMENT.md
  - [ ] Quick start instructions

- [ ] **API documentation is available**
  - [ ] Swagger docs at: https://your-domain.com/docs
  - [ ] ReDoc at: https://your-domain.com/redoc

- [ ] **Runbooks created for common tasks**
  - [ ] How to view logs
  - [ ] How to restart services
  - [ ] How to rollback
  - [ ] How to add new API key

---

## Final Validation

### Pre-Launch (24 hours before)

- [ ] **Smoke test all critical paths**
  - [ ] Login to admin dashboard
  - [ ] Send test WhatsApp message
  - [ ] Receive response
  - [ ] Check error logs dashboard

- [ ] **Monitor resource usage for 1 hour**
  ```bash
  watch -n 5 'docker stats'
  # Expected: CPU < 50%, Memory < 80%
  ```

- [ ] **Verify backup is working**
  ```bash
  /app/backup.sh
  ls -la /backups/dhanyada/
  # Expected: recent backup file exists
  ```

- [ ] **Test database restore procedure**
  - [ ] Create backup
  - [ ] Restore to test database
  - [ ] Verify data integrity
  - [ ] Expected: restore completes without errors

- [ ] **Load test with realistic traffic** (optional)
  ```bash
  # Simulate 10 messages/minute for 10 minutes
  for i in {1..100}; do
    curl -X POST https://your-domain.com/webhook/whatsapp \
      -H "Content-Type: application/json" \
      -d '{"message": "test"}' &
    sleep 6
  done
  # Monitor: docker stats, logs for errors
  ```

- [ ] **Stakeholder approval received**
  - [ ] All decision makers confirmed ready
  - [ ] Rollback plan discussed
  - [ ] On-call contact list created

### Launch Window

- [ ] **Notify all stakeholders of maintenance window** (if needed)
  - [ ] Timeline: start/end times
  - [ ] Expected downtime: 0 minutes (rolling deployment)
  - [ ] Support contact: (your info)

- [ ] **Perform final deployment**
  ```bash
  cd /app
  git pull origin main
  docker-compose down
  docker-compose pull
  docker-compose up -d
  docker-compose logs -f app
  # Wait 1 minute for startup
  ```

- [ ] **Run smoke tests post-deployment**
  ```bash
  curl https://your-domain.com/health  # Should be OK
  # Send test WhatsApp message
  # Check dashboard loads
  # Verify error logs empty or clean
  ```

- [ ] **Monitor for 1 hour after launch**
  - [ ] Watch application logs in real-time
  - [ ] Monitor error rate (should be 0%)
  - [ ] Check dashboard metrics look correct
  - [ ] Be ready to rollback if issues detected

### Post-Launch (24 hours)

- [ ] **All systems remain stable**
  ```bash
  # CPU usage: < 30% average
  # Memory: < 60% used
  # Error rate: < 0.1%
  # Response time: < 1 second p99
  ```

- [ ] **No critical errors in logs**
  ```bash
  docker-compose logs app | grep -i "critical\|fatal\|error" | head -20
  # Expected: no unexpected errors
  ```

- [ ] **Real users testing bot**
  - [ ] Ask farmer users to test bot
  - [ ] Collect feedback
  - [ ] Monitor for any issues

- [ ] **Backup/recovery tested in production**
  - [ ] Run backup: `/app/backup.sh`
  - [ ] Verify backup uploaded (if using S3)
  - [ ] Test restore to separate database

---

## Rollback Plan

If deployment fails, rollback is simple:

```bash
# 1. Stop new version
docker-compose down

# 2. Checkout previous version
git checkout HEAD~1

# 3. Restore database from backup (if needed)
docker-compose exec -T postgres pg_restore -U dhanyada -d dhanyada \
  < /backups/dhanyada/db_YYYYMMDD_HHMMSS.dump

# 4. Start previous version
docker-compose pull
docker-compose up -d

# 5. Verify
curl https://your-domain.com/health
```

**Estimated rollback time: < 5 minutes**

---

## Sign-Off

Production deployment approved by:

- [ ] **Developer:** _________________ Date: _______
- [ ] **DevOps/Ops:** _________________ Date: _______
- [ ] **Product Manager:** _________________ Date: _______
- [ ] **Security Review:** _________________ Date: _______

---

## Post-Deployment Notes

Use this section to document anything learned during deployment:

```
Date Deployed: _____________
Deployed By: ________________
Issues Encountered: ___________________________
Resolution: ________________________________
Follow-up Items: _____________________________
```

---

**Good luck with your deployment! 🚀**

If you encounter any issues, check [DEPLOYMENT.md](./DEPLOYMENT.md#troubleshooting) Troubleshooting section.
