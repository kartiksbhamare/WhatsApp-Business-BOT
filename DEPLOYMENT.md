# 🚀 Free Deployment Guide - WhatsApp Booking Bot

Deploy your salon booking bot **completely FREE** using Railway.

## 📋 Prerequisites

- [x] Your code is ready (✅ Done!)
- [x] Firebase database configured (✅ Done!)
- [x] Twilio WhatsApp account (✅ Done!)
- [ ] GitHub account
- [ ] Railway account (free)

---

## 🌟 Option 1: Railway (Recommended - EASIEST)

### Step 1: Push to GitHub

1. Create new repository on GitHub: https://github.com/new
2. Name it: `whatsapp-booking-bot`
3. Push your code:

```bash
git remote add origin https://github.com/YOUR_USERNAME/whatsapp-booking-bot.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Railway

1. Go to https://railway.app
2. Sign up with GitHub (free)
3. Click "Deploy from GitHub repo"
4. Select your `whatsapp-booking-bot` repository
5. Railway will auto-detect Python and deploy!

### Step 3: Set Environment Variables

In Railway dashboard → Your Project → Variables, add:

```
TWILIO_ACCOUNT_SID=YOUR_ACTUAL_TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN=YOUR_ACTUAL_TWILIO_AUTH_TOKEN
TWILIO_PHONE_NUMBER=YOUR_ACTUAL_WHATSAPP_NUMBER
APP_ENV=production
GOOGLE_CALENDAR_TIMEZONE=Asia/Kolkata
FIREBASE_CREDENTIALS=YOUR_ACTUAL_FIREBASE_CREDENTIALS_JSON
```

**Note**: Get your actual values from:
- Twilio Console for TWILIO_* variables
- Firebase Console for FIREBASE_CREDENTIALS (copy the entire JSON from firebase-key.json as one line)

### Step 4: Get Your App URL

- Railway will give you a URL like: `https://your-app-name.railway.app`
- Test it: `https://your-app-name.railway.app/api/services`

### Step 5: Update Twilio Webhook

1. Go to Twilio Console → WhatsApp → Sandbox
2. Set webhook URL to: `https://your-app-name.railway.app/webhook`
3. Save configuration

**🎉 DONE! Your app is live and FREE!**

---

## 🌟 Option 2: Render (Alternative Free Option)

### Step 1: Push to GitHub (same as above)

### Step 2: Deploy on Render

1. Go to https://render.com
2. Sign up with GitHub (free)
3. Click "New Web Service"
4. Connect your repository
5. Use these settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 3: Set Environment Variables (same as Railway)

### Step 4: Update Twilio Webhook with Render URL

---

## 🌟 Option 3: PythonAnywhere (Good for beginners)

### Step 1: Upload Files

1. Go to https://pythonanywhere.com (free account)
2. Upload your project files
3. Install requirements in console:

```bash
pip3.11 install --user -r requirements.txt
```

### Step 2: Create Web App

1. Web tab → Add new web app
2. Python 3.11
3. Manual configuration
4. Set source code path to your project
5. Edit WSGI file to use FastAPI

---

## 🔧 Environment Variables You Need

For any platform, set these variables:

```bash
TWILIO_ACCOUNT_SID=YOUR_ACTUAL_TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN=YOUR_ACTUAL_TWILIO_AUTH_TOKEN
TWILIO_PHONE_NUMBER=YOUR_ACTUAL_WHATSAPP_NUMBER
APP_ENV=production
GOOGLE_CALENDAR_TIMEZONE=Asia/Kolkata
FIREBASE_CREDENTIALS=YOUR_ACTUAL_FIREBASE_CREDENTIALS_JSON
```

## 📱 Testing Your Deployment

1. Check health: `https://your-app-url.com/`
2. Check services: `https://your-app-url.com/api/services`
3. Send WhatsApp to +14155238886
4. Check bookings: `https://your-app-url.com/api/bookings`

## 🎯 Free Tier Limits

| Platform | Hours/Month | Custom Domain | Database |
|----------|-------------|---------------|----------|
| Railway | 500 hours | ✅ Yes | Firebase (free) |
| Render | 750 hours | ✅ Yes | Firebase (free) |
| PythonAnywhere | Always on | ❌ Subdomain | Firebase (free) |

## 🚨 Important Notes

1. **Firebase credentials**: Set as FIREBASE_CREDENTIALS environment variable
2. **No ngrok needed**: Production deployment gives you a real URL
3. **Always free**: All platforms have permanent free tiers
4. **Automatic scaling**: Handles multiple WhatsApp messages
5. **SSL included**: All platforms provide HTTPS automatically

## 📞 Support

If you need help:
1. Check the logs in your deployment platform
2. Test endpoints manually
3. Verify Twilio webhook URL is correct

**Your salon booking bot will be live 24/7 for FREE! 🎉** 