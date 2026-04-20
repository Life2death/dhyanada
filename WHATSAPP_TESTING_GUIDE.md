# WhatsApp Testing Guide - Send Real Messages to Your Bot

**This guide shows HOW to test Dhanyada directly on WhatsApp**

---

## 📱 What You'll Learn

- ✅ How to set up WhatsApp Business Account
- ✅ How to connect your local code to WhatsApp
- ✅ How to send test messages from WhatsApp
- ✅ How to monitor responses in real-time
- ✅ How to debug failures

---

## 🔑 Prerequisites

### What You Need
1. **WhatsApp Business Account** (free but requires approval)
2. **Meta Business Manager Access** (free)
3. **ngrok** (free, for local testing)
4. **Postman** (optional, for manual webhook testing)
5. **Your Dhanyada code** (running locally)

### Time Required
- First setup: 30-60 minutes
- Testing after setup: 5 minutes per test

---

## 🚀 QUICK START (5 MINUTES)

### If You Already Have WhatsApp Business Account

```bash
# 1. Start Dhanyada locally
cd /c/Users/vikra/projects/dhanyada
uvicorn src.main:app --reload

# 2. Expose to internet with ngrok
ngrok http 8000
# Copy the URL: https://xxxx-xx-xxx-xxx-xx.ngrok.io

# 3. Update webhook URL in Meta Business Manager
# Settings > Configuration > Webhook URL
# Paste: https://xxxx-xx-xxx-xxx-xx.ngrok.io/webhook/whatsapp

# 4. Send message from WhatsApp!
# Message: "कांदा किंमत?"
# Expected: Price response in Marathi

# ✅ DONE!
```

---

## 📋 FULL SETUP GUIDE (First Time Only)

### STEP 1: Create WhatsApp Business Account

#### Option A: Using Existing Personal Account (Easiest)
```
1. Go to: https://www.whatsapp.com/business
2. Click "Get WhatsApp Business"
3. Choose "Use your existing personal number"
4. Verify your phone number
5. Create business account

⏱️ Time: 10 minutes
✅ Status: Business account created
```

#### Option B: Create New Business Number
```
1. Go to: https://developers.facebook.com/
2. Create Meta Business Account
3. Create WhatsApp Business Account
4. Set up phone number (can use virtual number)
5. Verify with SMS

⏱️ Time: 20 minutes
✅ Status: New business number ready
```

### STEP 2: Get WhatsApp Phone ID & Access Token

```
1. Go to: https://developers.facebook.com/
2. Navigation: Apps > Your App > WhatsApp > Getting Started
3. You'll see:
   ├─ Phone Number ID: xxxxxxxxxxxxxxxx
   ├─ Business Account ID: xxxxxxxxxxxxxxxx
   └─ Temporary Access Token: EABC...

4. Save these three values to .env file:
```

**Update .env file**:
```bash
# WhatsApp Configuration
WHATSAPP_PHONE_ID=120219707234567    # From Meta
WHATSAPP_TOKEN=EABC123xyz...        # From Meta  
WHATSAPP_BUSINESS_ACCOUNT_ID=102345  # From Meta
WHATSAPP_VERIFY_TOKEN=my_secret_123  # You create this - any string
```

### STEP 3: Install ngrok (Expose Local Server to Internet)

```bash
# Option A: Download from https://ngrok.com/download
# Or Option B: Install via package manager

# Windows (using chocolatey)
choco install ngrok

# Mac (using homebrew)
brew install ngrok

# Linux
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip
unzip ngrok-v3-stable-linux-amd64.zip

# Verify installation
ngrok --version
# Expected: ngrok version 3.x.x
```

### STEP 4: Start Your Dhanyada App

**Terminal 1: Start FastAPI**
```bash
cd /c/Users/vikra/projects/dhanyada

# Create/update .env file with WhatsApp credentials
# (See STEP 2 above)

# Start the app
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Expected:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

### STEP 5: Expose to Internet with ngrok

**Terminal 2: Start ngrok**
```bash
ngrok http 8000

# Expected output:
# Session Status                online
# Account                       free (upgrade)
# Version                       3.0.0
# Region                        us (United States)
# Latency                       45ms
# Web Interface                 http://127.0.0.1:4040
# 
# Forwarding    https://abc123-45-67-890.ngrok.io -> http://localhost:8000

# 📌 COPY THIS URL: https://abc123-45-67-890.ngrok.io
```

### STEP 6: Register Webhook with Meta

```
1. Go to: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started

2. In Meta Dashboard:
   Navigation: Apps > Your App > WhatsApp > Configuration

3. Paste webhook URL:
   Webhook URL: https://abc123-45-67-890.ngrok.io/webhook/whatsapp
   Verify Token: my_secret_123 (from .env WHATSAPP_VERIFY_TOKEN)

4. Click "Verify and Save"

5. Subscribe to messages:
   Webhook Fields: messages (checked ✅)

6. Success message: "Webhook updated"
```

### STEP 7: Test Webhook (Before Real Messages)

**Terminal 3: Test with curl**
```bash
# Test webhook verification (what Meta does)
curl -X GET "http://localhost:8000/webhook/whatsapp" \
  -G \
  -d "hub.mode=subscribe" \
  -d "hub.challenge=test_challenge_123" \
  -d "hub.verify_token=my_secret_123"

# Expected response:
# test_challenge_123

# If you see this, webhook is working! ✅
```

### STEP 8: Send Your First Test Message!

**From Your Phone**:
```
1. Open WhatsApp
2. Search for your WhatsApp Business Account number
3. Send message: "hello"

Expected in Terminal 1 (FastAPI logs):
# INFO: Received message from +919876543210: hello
# INFO: Intent classified: GREETING
# INFO: Sending response...

Expected on WhatsApp:
# "नमस्ते! मी Dhanyada आहे. तुम्हाला काय साहाय्य करू शकते?"
# (Hello! I'm Dhanyada. How can I help you?)
```

---

## 📊 REAL-WORLD TEST SCENARIOS

### TEST 1: Price Query
```
Message: "कांदा किंमत?"
Expected Response: 
  🌾 कांदा - पुणे मंडी
  💹 भाव: ₹4,200 - ₹4,500
  📊 आजचा दर: ₹4,350
  🏪 मंडी: पुणे (Agmarknet API)

Time: ~2 seconds
```

### TEST 2: Government Scheme Query
```
Message: "मला कोणती योजना मिळेल?"
Expected Response:
  ✅ तुम्हाला हे योजना मिळणार आहेत:
  1. PM-KISAN - ₹6,000/वर्ष
  2. PM-FASAL - पीक विमा
  3. राष्ट्रीय क्रांती - माती आरोग्य

Time: ~1 second
```

### TEST 3: Set Price Alert
```
Message: "कांदा ₹4000 से अधिक सूचित करो"
Expected Response:
  ✅ अलर्ट सेट झाली!
  कांदा > ₹4,000 होऊ शकेल तेव्हा तुम्हाला सूचित करेन

Database: price_alerts table updated

Time: ~0.5 seconds
```

### TEST 4: Pest Diagnosis
```
Message: [Send image of diseased crop]
Expected Response:
  🔍 आपण पाठवलेला हे संक्रमण दिसते:
  रोग: आलू लेट ब्लाइट
  कारण: बर्षाव + उच्च आर्द्रता
  उपाय: 
    - मेन्कोजेब स्प्रे करा
    - रोपे 25 सेमी अंतरे ठेवा

Time: ~3-5 seconds
```

### TEST 5: Weather Forecast
```
Message: "पुणे हवामान?"
Expected Response:
  ☀️ पुणे - 5 दिवसांचा अंदाज
  
  📅 आज: 35°C, 40% आर्द्रता, हलकी वारा
  📅 उद्या: 34°C, 45%, वाऱ्याचा अंदाज
  
  💧 अपेक्षित पाऊस: 10 मिमी

Time: ~1 second
```

---

## 🔍 MONITORING & DEBUGGING

### View Logs in Real-Time

**Terminal 1: Dhanyada Logs**
```bash
# Already running: uvicorn src.main:app --reload

# Watch logs (will auto-scroll)
# You'll see:
# INFO: 2026-04-18 10:30:45 | Webhook received from +919876543210
# INFO: Message text: कांदा किंमत?
# INFO: Intent: PRICE_QUERY, Confidence: 1.0
# INFO: Querying price repository...
# INFO: Response sent: ₹4,350

# To filter by farmer ID:
# grep "919876543210" app.log
```

### View ngrok Logs (All HTTP Traffic)

**ngrok Web Interface**:
```
1. Open: http://localhost:4040
2. Click "Inspect" tab
3. See all requests/responses
4. Click on request to see details:
   - Headers
   - Request body
   - Response body
   - Latency

This is VERY useful for debugging!
```

### Manual Webhook Testing with Postman

**Using Postman (Alternative to Real WhatsApp)**:
```
1. Download Postman: https://www.postman.com/downloads/

2. Create new POST request:
   URL: http://localhost:8000/webhook/whatsapp
   
3. Body (JSON):
   {
     "entry": [{
       "changes": [{
         "value": {
           "messages": [{
             "from": "919876543210",
             "text": {"body": "कांदा किंमत?"},
             "type": "text"
           }]
         }
       }]
     }]
   }

4. Click "Send"

5. Check response and logs

This lets you test without using WhatsApp!
```

---

## 🛠️ TROUBLESHOOTING

### Issue 1: "Webhook URL not reachable"
```
❌ Error: Meta can't reach your webhook

✅ Solution:
1. Check ngrok is running: ngrok http 8000
2. Check FastAPI is running: uvicorn running?
3. Copy ngrok URL exactly (https:// not http://)
4. Test locally first:
   curl http://localhost:8000/webhook/whatsapp
5. Wait 30 seconds for Meta to update
```

### Issue 2: "Challenge failed"
```
❌ Error: Verify token doesn't match

✅ Solution:
1. Check .env file: WHATSAPP_VERIFY_TOKEN=my_secret_123
2. Check Meta Dashboard has same token
3. Clear Meta cache: Remove and re-add webhook
4. Test: curl with token in URL
```

### Issue 3: "Message not received"
```
❌ Problem: WhatsApp sent message but bot didn't respond

✅ Debugging:
1. Check ngrok logs (http://localhost:4040)
2. See incoming request? 
   YES → Check FastAPI logs for error
   NO → Check webhook URL in Meta
3. Check phone numbers match
4. Try simpler message: "hello"
```

### Issue 4: "Response not sending back to WhatsApp"
```
❌ Problem: Bot processes but WhatsApp doesn't get reply

✅ Debugging:
1. Check WHATSAPP_TOKEN in .env (valid?)
2. Check WHATSAPP_PHONE_ID in .env (correct?)
3. Try manual POST with Postman (see above)
4. Check Meta logs for API errors
5. Verify number format: +919876543210
```

### Issue 5: "ngrok URL keeps changing"
```
❌ Problem: ngrok URL changes every time

✅ Solution:
1. Get paid ngrok account (keeps URL stable)
2. Or: Use static hostname
   ngrok http 8000 --domain=my-app.ngrok.io
3. Or: Update Meta webhook URL each time (annoying)

For now: Update webhook URL in Meta each time
```

---

## 📱 TEST MESSAGE LIBRARY

### Copy-Paste Messages to Test

#### MARATHI (मराठी)
```
Price Query:
"कांदा किंमत?"
"गहू आज किती?"
"बाजरी दर?"

Alert:
"कांदा ₹4000 से अधिक सूचित करो"
"गहू ₹2500 से कम होऊ शकेल तर बोला"

Scheme:
"मला कोणती योजना मिळेल?"
"PM-किसान अर्ह आहे?"

Greeting:
"नमस्ते"
"राम राम"

Help:
"मदत"
"तुम्हाला काय करता येते?"
```

#### ENGLISH
```
Price Query:
"What's the onion price?"
"Tell me wheat rate"
"Current cotton price?"

Alert:
"Alert when onion > 5000"
"Notify me if price drops below 3000"

Scheme:
"What schemes am I eligible for?"
"Tell me about PM-KISAN"

Greeting:
"Hi"
"Hello"
"Hey"

Help:
"Help"
"What can you do?"
"Menu"
```

#### HINGLISH (हिंग्लिश)
```
Price Query:
"kanda ki kimat?"
"soyabean rate bataao"

Alert:
"alert karo jab praat 4000 se upar jaye"

Scheme:
"mujhe kaun si yojana milegi?"

Greeting:
"hii"
"namaste"
```

---

## 📊 COMPLETE WORKFLOW (From Zero to Testing)

```
⏱️ TOTAL TIME: 45 minutes for first setup
              5 minutes for each test after

STEP 1 (10 min): Create WhatsApp Business Account
  ├─ Go to whatsapp.com/business
  ├─ Create account
  └─ Verify phone

STEP 2 (5 min): Get credentials
  ├─ Go to developers.facebook.com
  ├─ Copy Phone ID, Token, Account ID
  └─ Save to .env

STEP 3 (5 min): Install ngrok
  ├─ Download from ngrok.com
  ├─ Extract/install
  └─ Verify: ngrok --version

STEP 4 (3 min): Start Dhanyada
  ├─ cd dhanyada
  ├─ Update .env
  └─ uvicorn src.main:app --reload

STEP 5 (2 min): Start ngrok
  ├─ ngrok http 8000
  └─ Copy URL: https://xxxxx.ngrok.io

STEP 6 (10 min): Register webhook
  ├─ Go to Meta Dashboard
  ├─ Paste ngrok URL
  ├─ Paste verify token
  └─ Click Verify and Save

STEP 7 (3 min): Test with curl
  ├─ Test webhook locally first
  └─ Verify: Challenge response received

STEP 8 (2 min): Send real message
  ├─ Open WhatsApp app
  ├─ Message your bot
  └─ Check response

✅ READY TO TEST!
```

---

## 🚀 QUICK REFERENCE: Commands to Keep Open

**Keep these 3 terminals running side-by-side**:

```
┌─ TERMINAL 1 ─────────────────────────────────┐
│ $ uvicorn src.main:app --reload              │
│ INFO: Application startup complete           │
│ (Watch this for logs)                        │
└─────────────────────────────────────────────┘

┌─ TERMINAL 2 ─────────────────────────────────┐
│ $ ngrok http 8000                            │
│ Forwarding  https://abc123.ngrok.io -> ...   │
│ (Copy this URL)                              │
└─────────────────────────────────────────────┘

┌─ TERMINAL 3 ─────────────────────────────────┐
│ $ open http://localhost:4040                 │
│ (ngrok Web Inspector)                        │
└─────────────────────────────────────────────┘
```

---

## ✅ VERIFY SETUP IS WORKING

**Run this checklist**:

```
✅ 1. FastAPI running
   $ curl http://localhost:8000/docs
   Expected: Swagger UI loads

✅ 2. ngrok running
   $ curl https://<ngrok-url>/webhook/whatsapp
   Expected: Valid connection

✅ 3. Webhook test
   $ curl "http://localhost:8000/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=my_secret_123&hub.challenge=test123"
   Expected: test123 returned

✅ 4. Environment variables set
   $ env | grep WHATSAPP
   Expected: All three credentials shown

✅ 5. Database setup (if needed)
   $ psql -d dhanyada -c "SELECT 1"
   Expected: 1 (OK if PostgreSQL running)

✅ 6. Redis (if needed)
   $ redis-cli ping
   Expected: PONG

🟢 ALL GREEN? Ready to test on WhatsApp!
```

---

## 📞 LIVE TESTING CHECKLIST

When testing live on WhatsApp:

```
Before sending message:
☐ Check Terminal 1 (FastAPI logs visible?)
☐ Check Terminal 2 (ngrok running?)
☐ Check Terminal 3 (ngrok inspector open?)
☐ Check .env file has credentials
☐ Check Meta webhook is registered
☐ Check webhook URL is https://

Send message:
☐ Send from WhatsApp app
☐ Watch Terminal 1 for log message
☐ Watch Terminal 3 ngrok inspector
☐ Check WhatsApp for response

Debug if no response:
☐ Check Terminal 1 for errors
☐ Check Terminal 3 for HTTP request
☐ Check bot processed intent correctly
☐ Check WHATSAPP_TOKEN is valid
```

---

## 🎯 NEXT STEPS

### TODAY (45 minutes)
```
1. Set up WhatsApp Business Account
2. Get credentials
3. Install ngrok
4. Register webhook
5. Send first test message
```

### TOMORROW (Optional)
```
1. Test all scenarios from above
2. Set up price alerts
3. Test image upload (if pest diagnosis enabled)
4. Test multi-language messages
```

### THIS WEEK
```
1. Stress test with 10+ messages
2. Test error handling
3. Monitor logs and performance
4. Document any issues found
```

---

## 📚 Additional Resources

- **Meta WhatsApp API Docs**: https://developers.facebook.com/docs/whatsapp/cloud-api
- **ngrok Documentation**: https://ngrok.com/docs
- **Postman Download**: https://www.postman.com/downloads/
- **WhatsApp Business FAQ**: https://www.whatsapp.com/business/faq

---

## 🆘 STILL STUCK?

### Common Issues Quick Fix:

| Problem | Quick Fix |
|---------|-----------|
| "Webhook not reachable" | `ngrok http 8000` + wait 30s |
| "Verify token failed" | Check .env matches Meta dashboard |
| "No response back" | Check logs in Terminal 1 |
| "ngrok URL keeps changing" | Update webhook each time or get paid account |
| "Message doesn't arrive at bot" | Check phone number format: +919876543210 |

---

**Status**: ✅ Ready to Test on WhatsApp!  
**Next**: Follow steps above and send your first message!
