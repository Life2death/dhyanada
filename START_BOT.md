# 🚀 How to Start & Test Your Kisan AI WhatsApp Bot

## ✅ Prerequisites
- Python 3.10+
- Credentials in `.env` (already configured with permanent token)
- Meta WhatsApp webhook URL configured

## 🔧 Step 1: Install Dependencies

```bash
cd ~/projects/kisan-ai
pip install fastapi uvicorn pywa pytest
```

## ▶️ Step 2: Start the Bot

```bash
cd ~/projects/kisan-ai
uvicorn src.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 [CTRL+C to quit]
INFO:     Application startup complete
✅ WhatsApp adapter initialized
```

## 🧪 Step 3: Test Locally (in another terminal)

```bash
# Health check
curl http://localhost:8000/health

# Status endpoint
curl http://localhost:8000/status
```

## 📱 Step 4: Configure Meta Webhook (One-time setup)

1. Go to [Meta Business Console](https://business.facebook.com/)
2. Navigate to: **Kisan Tech** → **WhatsApp** → **Configuration**
3. Click **Edit** next to "Webhook URL"
4. Set:
   - **Webhook URL**: `https://YOUR_DOMAIN:8000/webhook/whatsapp`
   - **Verify Token**: `kisan_webhook_token`
   - **Subscribe to webhook fields**: `messages`, `message_status`

5. Click **Verify and Save**

## 📲 Step 5: Send Test Message

1. Use your Meta test phone number (from WhatsApp Business Account)
2. Send a message to your bot's phone number
3. Watch the bot logs - you should see:
   ```
   📱 Message from 919876543210: नमस्कार
   ```

## 📝 Example Test Messages

```
"मंडी दर" (Marathi: "Mandi rates")
"खांडा" (Marathi: "Sugar cane")
"शेतकरी" (Marathi: "Farmer")
```

## ✅ What the Bot Currently Does

- ✅ Receives messages from WhatsApp
- ✅ Detects Marathi language automatically
- ✅ Logs all incoming messages
- ✅ Returns 200 OK to Meta (acknowledges receipt)

## ⏭️ What's Next (Coming Soon)

- Module 3: Database (Postgres + Redis)
- Module 4: Mandi Price API
- Module 5: Intent Classifier
- Response generation (send prices back to farmer)

## 🔑 Important Notes

- **Token is permanent** (no expiration) ✅
- Keep `.env` SECRET (never commit to git)
- Logs show Marathi detection working
- Test with your actual WhatsApp test phone

---

**Happy Testing!** 🚀
