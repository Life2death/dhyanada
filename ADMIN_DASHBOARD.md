# Admin Dashboard Guide

## Overview

The Kisan AI Admin Dashboard provides real-time monitoring of:
- 📊 **Daily Active Users (DAU)** — 7-day and 30-day trends
- 📱 **Message Analytics** — Incoming/outgoing volume by date
- 🌾 **Top Commodities** — Most searched crops
- 📈 **Subscription Funnel** — User journey breakdown
- 📡 **Broadcast Status** — Last daily broadcast results
- 💬 **Recent Messages** — Last 50 conversations (anonymized)

---

## Quick Start

### 1. Access the Dashboard

Open your browser and go to:
```
http://localhost:8000/admin/
```

You'll be redirected to the login page if you don't have a valid token.

### 2. Login

**Default Credentials**:
- Username: `admin`
- Password: `changeme`

⚠️ **WARNING**: Change these credentials in production! Update your `.env` file:
```
ADMIN_USERNAME=your_secure_username
ADMIN_PASSWORD=your_secure_password
JWT_SECRET=your_random_secret_key
```

### 3. View Dashboard

After login, you'll see:
- Real-time metrics cards
- Message volume charts
- Top commodities list
- Subscription funnel breakdown
- Recent conversation logs
- Broadcast job status

---

## Features

### Real-Time Metrics

**Daily Active Users (DAU)**
- Shows today's active farmers
- Compares 7-day and 30-day trends
- Tracks growth rate

**Message Volume**
- Incoming messages (user to bot)
- Outgoing messages (bot to user)
- Daily breakdown for last 7 days

**Top Commodities**
- Lists top 10 crops searched by farmers
- Shows query count for each
- Updates as new messages arrive

**Subscription Funnel**
- New farmers (just registered)
- Awaiting consent (not opted in)
- Active subscribers (receiving broadcasts)
- Opted out (unsubscribed)

**Recent Messages**
- Last 50 messages
- Farmer phone (masked as XXX-XXX-5432)
- Message preview
- Detected intent
- Direction (inbound/outbound)

**Broadcast Health**
- Last broadcast timestamp
- Sent count
- Failed count
- Status (success/partial/failed)

---

## Auto-Refresh

The dashboard automatically refreshes data every **5 minutes**.

You can:
- Manually refresh by pressing `F5` or closing/reopening the page
- Logout and login to clear the cache
- Monitor multiple dashboards simultaneously (use different tabs)

---

## Security

### Authentication

- **JWT Tokens**: One-hour expiration
- **HTTPBearer**: Token sent in `Authorization` header
- **Logout**: Clears token from browser storage

### Token Refresh

Tokens expire after 1 hour. You'll be automatically redirected to login when your token expires.

### What's Visible

The dashboard only shows:
- Aggregated metrics (DAU, message counts)
- Anonymized farmer data (phone number masked)
- Intent detection (no sensitive message content)
- Broadcast status (counts, not content)

---

## API Endpoints

All endpoints require JWT token in `Authorization: Bearer <token>` header.

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `GET /admin/login` | Login form | HTML form |
| `POST /admin/login` | Generate token | JSON: `{access_token, token_type}` |
| `GET /admin/` | Dashboard | HTML page |
| `GET /admin/api/dashboard` | Full snapshot | All metrics |
| `GET /admin/api/dau` | Daily active users | DAU number |
| `GET /admin/api/messages` | Message volume | Daily breakdown |
| `GET /admin/api/crops` | Top commodities | Crop list with counts |
| `GET /admin/api/funnel` | Subscription states | User counts by state |
| `GET /admin/api/messages-log` | Recent messages | Last N messages |
| `GET /admin/api/broadcast-health` | Broadcast status | Last job details |

---

## Troubleshooting

### "Invalid credentials"

- Verify you're using the correct username and password
- Default is `admin` / `changeme`
- Check `.env` file for custom credentials

### "Token expired, please login again"

- Your session has expired (1 hour max)
- Click logout and login again
- This is normal — it's a security feature

### "No data showing"

- Dashboard requires live farmer activity
- Check if WhatsApp bot is running
- Ensure farmers are sending messages
- Wait for first message to appear

### Page is blank

- Check browser console for errors (F12)
- Verify JavaScript is enabled
- Try clearing browser cache
- Try incognito/private mode

### Metrics are old

- Auto-refresh happens every 5 minutes
- Manually refresh: `F5` or `Cmd+R`
- Check if bot is processing messages

---

## Production Setup

### Step 1: Update Credentials

Edit `.env`:
```
ADMIN_USERNAME=your_username
ADMIN_PASSWORD=your_secure_password
JWT_SECRET=generate_with: openssl rand -base64 32
JWT_EXPIRY_HOURS=1
```

Generate JWT secret:
```bash
openssl rand -base64 32
```

### Step 2: Enable HTTPS

The dashboard **must be served over HTTPS** in production.

Use a reverse proxy (nginx, Apache) or load balancer (AWS ELB, Google Load Balancer).

Example nginx config:
```nginx
server {
    listen 443 ssl http2;
    server_name dhanyada.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /admin {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Authorization $http_authorization;
    }
}
```

### Step 3: Rate Limiting (Optional)

Add rate limiting to login endpoint to prevent brute force:

```nginx
limit_req_zone $binary_remote_addr zone=login:10m rate=3r/m;

location /admin/login {
    limit_req zone=login burst=5;
    proxy_pass http://127.0.0.1:8000;
}
```

### Step 4: Monitor Access

Log all admin access:

```bash
# Check FastAPI logs for /admin requests
tail -f app.log | grep "/admin"
```

---

## Best Practices

✅ **DO**:
- Change default credentials in `.env`
- Use HTTPS in production
- Rotate JWT_SECRET regularly
- Monitor access logs
- Review metrics daily
- Keep FastAPI updated

❌ **DON'T**:
- Share login credentials
- Use over HTTP (unencrypted)
- Hardcode secrets in code
- Expose dashboard to public internet
- Commit `.env` to git

---

## Next Steps

After setup, consider:

1. **Monitoring & Alerts** (Phase 3 Step 3)
   - Email alerts for broadcast failures
   - Error rate monitoring
   - Price data freshness checks

2. **Deployment** (Phase 3 Step 4)
   - Docker containerization
   - CI/CD with GitHub Actions
   - Scaling guidelines

3. **Advanced Features**
   - 2FA for admin login
   - Audit logging
   - Custom metrics/reports
   - Admin user management

---

## Support

For issues, check:
1. **Browser Console**: Press F12 → Console tab for JS errors
2. **FastAPI Logs**: Check server terminal for errors
3. **Database**: Verify PostgreSQL/SQLite is running
4. **Network**: Ensure ngrok/reverse proxy is active

---

**Version**: 1.0
**Updated**: April 2026
**Status**: Production Ready
