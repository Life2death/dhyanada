# WHERE & HOW TO EXECUTE - Step-by-Step Visual Guide

**This shows you EXACTLY where to run each command**

---

## 📍 YOUR WORKING LOCATION

### Current Location on Your Computer
```
C:\Users\vikra\projects\kisan-ai\  ← YOU ARE HERE
```

### Verify You're in Right Folder
```bash
# Open PowerShell or CMD and check:
cd C:\Users\vikra\projects\kisan-ai
pwd
# Expected output:
# Path
# ----
# C:\Users\vikra\projects\kisan-ai
```

---

## 🖥️ YOU NEED 3 TERMINAL WINDOWS

### Open Multiple Terminals (Choose Your Method)

#### **Method A: Windows PowerShell** (Recommended for Windows)
```
1. Click Windows Start button
2. Type "PowerShell"
3. Click "Windows PowerShell"
4. A black window opens

✅ This is Terminal 1 (or 2, or 3 depending on which you open)
```

#### **Method B: Windows Command Prompt (CMD)**
```
1. Click Windows Start button
2. Type "cmd"
3. Click "Command Prompt"
4. A black window opens

✅ This works the same as PowerShell
```

#### **Method C: Git Bash** (If you have it)
```
1. Right-click on folder
2. Click "Git Bash Here"
3. Terminal opens in that folder

✅ Best option - you're already in right location!
```

---

## 📋 STEP-BY-STEP EXECUTION

### STEP 1: Navigate to Project (All Terminals)

```bash
# Type this in EACH new terminal you open:
cd C:\Users\vikra\projects\kisan-ai

# Verify you're there:
pwd
# Expected: C:\Users\vikra\projects\kisan-ai

dir  # List files to verify
# You should see: src/, tests/, .env, README.md, etc.
```

**Visual**:
```
┌─ PowerShell ─────────────────────────┐
│ PS C:\Users\vikra> cd C:\Users\vikra\projects\kisan-ai
│ PS C:\Users\vikra\projects\kisan-ai> pwd
│ C:\Users\vikra\projects\kisan-ai
│ PS C:\Users\vikra\projects\kisan-ai>                    
└───────────────────────────────────────┘
                ✅ Ready!
```

---

### STEP 2: Open 3 Terminal Windows Side-by-Side

**Arrange on your screen**:
```
┌──────────────────────────────────────────────────────────────┐
│                    Your Desktop (1920x1080)                  │
├─────────────────────┬─────────────────────┬─────────────────┤
│                     │                     │                 │
│   Terminal 1        │   Terminal 2        │   Terminal 3    │
│   (FastAPI)         │   (ngrok)           │   (Monitor)     │
│                     │                     │                 │
│   Width: ~640px     │   Width: ~640px     │   Width: ~640px │
│                     │                     │                 │
└─────────────────────┴─────────────────────┴─────────────────┘

Tip: Arrange using Windows Snap
  - Drag window to left edge → snaps to left half
  - Drag another to right edge → snaps to right half
```

---

## 🚀 EXECUTE COMMANDS NOW

### TERMINAL 1: START FASTAPI

```bash
# Make sure you're in right directory first:
cd C:\Users\vikra\projects\kisan-ai

# Then run:
uvicorn src.main:app --reload

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
# ✅ DO NOT CLOSE THIS TERMINAL - Keep it running!
```

**Visual - Before Running**:
```
┌─ Terminal 1 (FastAPI) ────────────────────────────────┐
│ PS C:\Users\vikra\projects\kisan-ai> uvicorn src.main:app --reload
│ (waiting...)
│
│
│
│
└───────────────────────────────────────────────────────┘
```

**Visual - After Running**:
```
┌─ Terminal 1 (FastAPI) ────────────────────────────────┐
│ PS C:\Users\vikra\projects\kisan-ai> uvicorn src.main:app --reload
│ INFO:     Uvicorn running on http://0.0.0.0:8000
│ INFO:     Application startup complete
│ (cursor blinking - keeps running)
│
│ 🟢 KEEP THIS RUNNING - This is your bot!
└───────────────────────────────────────────────────────┘
```

**What if you see error**:
```
❌ Error: "Address already in use"
✅ Solution: Run on different port
   uvicorn src.main:app --reload --port 8001

❌ Error: "Module not found"
✅ Solution: Install dependencies
   pip install -r requirements.txt
   Then run uvicorn again
```

---

### TERMINAL 2: START NGROK (New Window)

**Keep Terminal 1 running, open NEW terminal**:

```bash
# 1. Navigate to project directory (same as Terminal 1)
cd C:\Users\vikra\projects\kisan-ai

# 2. Start ngrok
ngrok http 8000

# You should see:
# Session Status                online
# Version                       3.0.0
# Forwarding    https://abc123-45-67-890.ngrok.io -> http://localhost:8000
#
# ✅ Copy the https:// URL - you'll need it!
```

**Visual - Before Running**:
```
┌─ Terminal 2 (ngrok) ──────────────────────────────────┐
│ PS C:\Users\vikra\projects\kisan-ai> ngrok http 8000
│ (waiting...)
│
│
│
│
└───────────────────────────────────────────────────────┘
```

**Visual - After Running**:
```
┌─ Terminal 2 (ngrok) ──────────────────────────────────┐
│ PS C:\Users\vikra\projects\kisan-ai> ngrok http 8000
│
│ Session Status                online
│ Account                       free (Plan: Free)
│ Version                       3.0.0
│ Region                        United States (us)
│ Latency                       45ms
│ Web Interface                 http://127.0.0.1:4040
│
│ Forwarding    https://abc123-45-67-890.ngrok.io -> http://localhost:8000
│ Forwarding    http://abc123-45-67-890.ngrok.io -> http://localhost:8000
│
│ 📌 IMPORTANT: Copy this URL: https://abc123-45-67-890.ngrok.io
│ ✅ Keep this running!
└───────────────────────────────────────────────────────┘
```

**What if you see error**:
```
❌ Error: "ngrok not found"
✅ Solution: Install ngrok
   # Windows PowerShell (as Admin):
   choco install ngrok
   
   # Or download: https://ngrok.com/download
   # Extract to: C:\Program Files\ngrok\
   # Add to PATH

❌ Error: "Port 8000 already in use"
✅ Solution: Port might be in use
   - Check if FastAPI started correctly in Terminal 1
   - Or use different port: ngrok http 8001
```

---

### TERMINAL 3: MONITOR REQUESTS (Optional)

**Keep Terminals 1 & 2 running, open NEW terminal**:

```bash
# Option A: Open ngrok Web Inspector in browser
start http://localhost:4040

# OR Option B: Just monitor Terminal 1 logs
# Watch Terminal 1 for incoming messages

# ✅ You can now see all WhatsApp requests coming through!
```

**Visual**:
```
┌─ Web Browser (ngrok Inspector) ────────────────────────┐
│ http://localhost:4040                                  │
│                                                         │
│ [Inspect]  [Status]  [Auth]                           │
│                                                         │
│ Requests:                                              │
│ ├─ POST /webhook/whatsapp  200 OK  45ms               │
│ ├─ POST /webhook/whatsapp  200 OK  52ms               │
│ └─ POST /webhook/whatsapp  200 OK  38ms               │
│                                                         │
│ Shows all WhatsApp messages coming in! ✅             │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 CONFIGURE WHATSAPP (Via Web Browser)

### STEP 3: Get Meta Credentials

```
1. Open web browser
2. Go to: https://developers.facebook.com
3. Log in to your account
4. Go to: Apps > Your App > WhatsApp > Configuration
5. You'll see:
   - Phone Number ID: (copy this)
   - Access Token: (copy this)
   - Business Account ID: (copy this)
```

**Visual**:
```
┌─ Firefox / Chrome / Edge ─────────────────────────────┐
│ https://developers.facebook.com                      │
│                                                       │
│ WhatsApp Configuration                               │
│ ├─ Phone Number ID: 120219707234567                  │
│ ├─ Access Token: EABC123xyz...                       │
│ └─ Business Account ID: 102345                       │
│                                                       │
│ ✅ Copy these 3 values                               │
└───────────────────────────────────────────────────────┘
```

### STEP 4: Update .env File

```bash
# In Terminal 1, 2, or 3 (doesn't matter), open .env:
# Windows: Open in Notepad

# Navigate to: C:\Users\vikra\projects\kisan-ai
# Find file: .env
# Double-click to open in Notepad

# Add these lines (replace xxx with your values):
WHATSAPP_PHONE_ID=120219707234567
WHATSAPP_TOKEN=EABC123xyz...
WHATSAPP_BUSINESS_ACCOUNT_ID=102345
WHATSAPP_VERIFY_TOKEN=my_secret_123

# Save file (Ctrl+S)
```

**Visual - .env File**:
```
┌─ Notepad - .env ──────────────────────────────────────┐
│ # WhatsApp Configuration                             │
│ WHATSAPP_PHONE_ID=120219707234567                    │
│ WHATSAPP_TOKEN=EABC123xyz...                         │
│ WHATSAPP_BUSINESS_ACCOUNT_ID=102345                  │
│ WHATSAPP_VERIFY_TOKEN=my_secret_123                  │
│                                                       │
│ # Database                                            │
│ DATABASE_URL=postgresql://...                        │
│ REDIS_URL=redis://...                                │
│                                                       │
│ [Save] ✅                                             │
└───────────────────────────────────────────────────────┘
```

### STEP 5: Register Webhook in Meta

```
1. Still in: https://developers.facebook.com
2. Find: Webhook URL field
3. Paste the ngrok URL from Terminal 2:
   https://abc123-45-67-890.ngrok.io/webhook/whatsapp

4. Find: Verify Token field
5. Paste: my_secret_123

6. Click: "Verify and Save"

7. Wait 30 seconds for Meta to update

✅ Webhook is now registered!
```

**Visual**:
```
┌─ Meta Dashboard ──────────────────────────────────────┐
│ Webhook Configuration                                │
│                                                       │
│ Webhook URL:                                          │
│ [https://abc123-45-67-890.ngrok.io/webhook/whatsapp]│
│                                                       │
│ Verify Token:                                         │
│ [my_secret_123]                                      │
│                                                       │
│ [Verify and Save] ✅                                  │
│                                                       │
│ ✅ Webhook updated successfully!                      │
└───────────────────────────────────────────────────────┘
```

---

## 📱 SEND FIRST MESSAGE (WhatsApp App)

### STEP 6: Send Test Message

```
1. Open WhatsApp on your phone

2. Search for your bot account number
   (The WhatsApp Business number you created)

3. Send a test message:
   "कांदा किंमत?"
   
   OR in English:
   "What's the onion price?"

4. Wait 2-3 seconds...

5. Get response:
   "🌾 कांदा - पुणे मंडी
   💹 भाव: ₹4,200..."
   
   ✅ YOUR BOT WORKS!
```

**Visual - WhatsApp Chat**:
```
┌─ WhatsApp Chat ───────────────────────────────────────┐
│                                                        │
│ You: कांदा किंमत?                                     │
│ [Sent 10:30 AM]                                       │
│                                                        │
│ Kisan AI: 🌾 कांदा - पुणे मंडी               [10:30 AM]
│           💹 भाव: ₹4,200 - ₹4,500                    │
│           📊 आजचा दर: ₹4,350                          │
│           🏪 मंडी: पुणे (Agmarknet)                    │
│                                                        │
│ ✅ LIVE! Your bot is responding!                      │
└────────────────────────────────────────────────────────┘
```

---

## 🔍 MONITOR IN REAL-TIME

### Watch Logs While Testing

```
Keep looking at Terminal 1 while you send message:

You'll see output like:
INFO: Received webhook from WhatsApp
INFO: From phone: +919876543210
INFO: Message text: कांदा किंमत?
INFO: Intent classified: PRICE_QUERY
INFO: Query status: success
INFO: Sending response...
INFO: Response sent

✅ This means your bot is working!
```

**Visual - Terminal 1 With Logs**:
```
┌─ Terminal 1 (FastAPI with logs) ──────────────────────┐
│ INFO:     Application startup complete                │
│                                                        │
│ 2026-04-18 10:30:45 | INFO: Received webhook         │
│ 2026-04-18 10:30:45 | INFO: From: +919876543210      │
│ 2026-04-18 10:30:45 | INFO: Message: कांदा किंमत?   │
│ 2026-04-18 10:30:45 | INFO: Intent: PRICE_QUERY      │
│ 2026-04-18 10:30:46 | INFO: Querying price API...    │
│ 2026-04-18 10:30:47 | INFO: Response: ₹4,200-4,500   │
│ 2026-04-18 10:30:47 | INFO: WhatsApp message sent ✅  │
│                                                        │
│ (cursor blinking - waiting for next message)          │
│                                                        │
│ ✅ Bot is running and responding!                     │
└────────────────────────────────────────────────────────┘
```

---

## 🎯 COMPLETE EXECUTION CHECKLIST

```
TERMINAL 1 (FastAPI):
☐ Navigate to: C:\Users\vikra\projects\kisan-ai
☐ Run: uvicorn src.main:app --reload
☐ See: "Application startup complete"
☐ Keep terminal OPEN and running

TERMINAL 2 (ngrok):
☐ Navigate to: C:\Users\vikra\projects\kisan-ai
☐ Run: ngrok http 8000
☐ See: "Forwarding https://xxxxx.ngrok.io"
☐ Copy the https:// URL
☐ Keep terminal OPEN and running

META DASHBOARD:
☐ Go to: https://developers.facebook.com
☐ Find: Webhook Configuration
☐ Paste: https://xxxxx.ngrok.io/webhook/whatsapp
☐ Paste verify token: my_secret_123
☐ Click: "Verify and Save"
☐ Wait: 30 seconds for update

WHATSAPP APP (On Your Phone):
☐ Open WhatsApp
☐ Find your bot account
☐ Send: "कांदा किंमत?"
☐ Get: Price response in Marathi
☐ Check Terminal 1 for logs

✅ ALL DONE! Bot is live!
```

---

## 🆘 TROUBLESHOOTING BY LOCATION

### Problem: "Command not found" in Terminal

**Solution**: You're not in right directory!

```bash
# Current location might be:
C:\Users\vikra>

# You need:
C:\Users\vikra\projects\kisan-ai>

# Fix it:
cd C:\Users\vikra\projects\kisan-ai
pwd  # Verify
```

### Problem: "Cannot connect to localhost:8000"

**Solution**: FastAPI not running in Terminal 1

```bash
# In Terminal 1:
✅ Check you ran: uvicorn src.main:app --reload
✅ Check you see: "Application startup complete"
✅ Keep Terminal 1 open (don't close it!)

# If Terminal 1 shows error:
pip install -r requirements.txt  # Install dependencies
uvicorn src.main:app --reload    # Try again
```

### Problem: "ngrok not found"

**Solution**: ngrok not installed

```bash
# Install ngrok:
choco install ngrok  # If you have Chocolatey

# OR download manually:
# 1. Go to: https://ngrok.com/download
# 2. Download for Windows
# 3. Extract to: C:\Program Files\ngrok\
# 4. Add to PATH:
#    - Right-click Start button
#    - System > Advanced system settings
#    - Environment Variables
#    - Add C:\Program Files\ngrok\ to PATH

# Verify:
ngrok --version
```

### Problem: "Webhook URL not reachable"

**Solution**: ngrok URL needs to be updated in Meta

```bash
# Check Terminal 2:
✅ ngrok is running? (should see "Forwarding")
✅ Copy exact URL: https://abc123...

# In Meta Dashboard:
✅ Go to Webhook Configuration
✅ Clear old URL
✅ Paste new URL exactly
✅ Click "Verify and Save"
✅ Wait 30 seconds
✅ Try WhatsApp message again
```

---

## ✅ VERIFY EVERYTHING IS WORKING

```bash
# In Terminal 1, you should see:
✅ "Application startup complete"

# In Terminal 2, you should see:
✅ "Forwarding https://xxxxx.ngrok.io -> http://localhost:8000"

# In ngrok Web Inspector (localhost:4040):
✅ POST /webhook/whatsapp requests appearing

# In WhatsApp:
✅ Messages being sent to bot
✅ Responses coming back

🟢 ALL GREEN? Your bot is LIVE!
```

---

## 📊 YOUR 3-TERMINAL LAYOUT (Side by Side)

**Recommended Desktop Arrangement**:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  Terminal 1      │  │  Terminal 2      │  │  Browser     │ │
│  │  (FastAPI)       │  │  (ngrok)         │  │  (ngrok:4040)│ │
│  │                  │  │                  │  │              │ │
│  │ ✅ Running       │  │ ✅ Running       │  │ 🌐 Monitor   │ │
│  │                  │  │                  │  │              │ │
│  │ [Logs showing]   │  │ [URL showing]    │  │ [Requests]   │ │
│  │ incoming         │  │ Forwarding: -->  │  │ showing      │ │
│  │ messages         │  │ http://localhost │  │              │ │
│  │                  │  │ :8000            │  │              │ │
│  │                  │  │                  │  │              │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
│                                                                 │
│  + Phone with WhatsApp (bottom right corner)                  │
│    Sending messages to bot                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**How to arrange on Windows**:
```
1. Drag Terminal 1 window to left side
   - Window automatically snaps to left half

2. Drag Terminal 2 window to right side
   - Window automatically snaps to right half

3. Open browser in Terminal 3 or separate browser window
   - Position below or overlapping

4. Use Alt+Tab to switch between windows

5. All 3 running simultaneously!
```

---

## 🚀 READY TO START?

### Execute Right Now:

```bash
# 1. Open PowerShell
# 2. Run:
cd C:\Users\vikra\projects\kisan-ai

# 3. Then in SAME Terminal:
uvicorn src.main:app --reload

# 4. Open ANOTHER PowerShell
# 5. Run:
cd C:\Users\vikra\projects\kisan-ai
ngrok http 8000

# 6. Look for: https://xxxxx.ngrok.io
# 7. Update in Meta Dashboard
# 8. Send WhatsApp message!

✅ YOU'RE LIVE!
```

---

## 📞 NEED HELP?

**Check your setup**:
```bash
# Verify FastAPI is running
curl http://localhost:8000/docs
# Should open Swagger UI in browser

# Verify ngrok is forwarding
curl https://localhost:4040
# Should show ngrok dashboard

# Check your message reaches bot
# Watch Terminal 1 logs
# Should see incoming message
```

---

**Status**: ✅ Ready to execute!  
**Time**: 5 minutes to live bot  
**Location**: C:\Users\vikra\projects\kisan-ai  
**Next**: Follow checkboxes above and send first message!
