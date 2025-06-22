# 🚀 Venom Bot Setup Guide

## Migration from Twilio to Venom Bot

Congratulations on switching to Venom Bot! This guide will help you transition from Twilio to a completely **FREE** WhatsApp solution.

## 🆚 Before vs After

### Before (Twilio)
- ❌ **Paid service** - costs per message
- ❌ **Limited trial** - only 9 messages/day
- ❌ **Complex setup** - webhooks, phone verification
- ❌ **Sandbox limitations** - recipient verification required

### After (Venom Bot)
- ✅ **Completely FREE** - no message limits
- ✅ **Full WhatsApp features** - rich media, groups, etc.
- ✅ **Easy setup** - just scan QR code
- ✅ **No limitations** - message anyone

## 📋 Prerequisites

Before starting, ensure you have:
- ✅ Node.js 16+ installed
- ✅ Python 3.8+ installed
- ✅ Chrome/Chromium browser (for headless WhatsApp Web)
- ✅ WhatsApp account for the bot
- ✅ Firebase project setup

## 🔧 Step-by-Step Setup

### Step 1: Remove Old Twilio Configuration

1. **Remove Twilio environment variables** from your `.env` file:
   ```bash
   # Remove these lines:
   TWILIO_ACCOUNT_SID=...
   TWILIO_AUTH_TOKEN=...
   TWILIO_PHONE_NUMBER=...
   ```

2. **Add Venom Bot configuration**:
   ```bash
   # Add these lines:
   VENOM_SERVICE_URL=http://localhost:3000
   FIREBASE_PROJECT_ID=your-firebase-project-id
   ```

### Step 2: Install Node.js Dependencies

```bash
# Install Venom Bot and dependencies
npm install
```

### Step 3: Test Venom Bot (Optional)

```bash
# Test if Venom Bot can initialize
node test-venom.js
```

### Step 4: Start Services

#### Option A: Using the Start Script (Recommended)
```bash
./start-services.sh
```

#### Option B: Manual Start
**Terminal 1** - Start Venom Bot service:
```bash
node venom-service.js
```

**Terminal 2** - Start FastAPI application:
```bash
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 5: Connect WhatsApp

1. **Wait for QR Code**: When Venom Bot starts, it will generate a QR code
2. **Check the logs**: Look in terminal or `venom.log` file for the QR code
3. **Scan with WhatsApp**:
   - Open WhatsApp on your phone
   - Go to Settings → Connected Devices → Link a Device
   - Scan the QR code
4. **Wait for confirmation**: You'll see "✅ Venom Bot initialized successfully!"

## 📱 Testing Your Bot

1. **Send a test message** to your connected WhatsApp number
2. **Type "hi"** to start the booking conversation
3. **Follow the prompts** to test the full booking flow

## 🔍 Troubleshooting

### Common Issues & Solutions

#### QR Code Not Showing
```bash
# Check the log file
tail -f venom.log

# Or restart the service
# Ctrl+C to stop, then restart
node venom-service.js
```

#### WhatsApp Connection Lost
```bash
# Delete session files and restart
rm -rf tokens/
rm -rf .wwebjs_auth/
rm -rf session/
node venom-service.js
```

#### Port Already in Use
```bash
# Check what's using port 3000
lsof -i :3000

# Kill the process if needed
kill -9 <PID>

# Or change the port in venom-service.js
```

#### Python Service Can't Connect to Venom
```bash
# Check if Venom service is running
curl http://localhost:3000/health

# Should return: {"status":"ready","timestamp":"..."}
```

## 🚀 Deployment Considerations

### Development Environment
- Venom Bot runs locally and connects to WhatsApp Web
- Perfect for testing and development

### Production Environment
- Consider using a VPS or cloud server
- Ensure stable internet connection
- Monitor the Venom Bot service for disconnections
- Implement auto-restart mechanisms

### Recommended Deployment Stack
1. **VPS with Ubuntu** (DigitalOcean, AWS EC2, etc.)
2. **PM2** for process management
3. **Nginx** for reverse proxy
4. **Let's Encrypt** for SSL certificates

## 💡 Tips for Success

### 1. Keep Your WhatsApp Active
- The bot uses WhatsApp Web, so keep your main WhatsApp active
- Avoid logging out from WhatsApp Web on other devices

### 2. Monitor Logs
```bash
# Keep an eye on both services
tail -f venom.log
# and
tail -f your-fastapi-logs
```

### 3. Backup Your Session
```bash
# Backup session files to avoid re-scanning QR codes
cp -r tokens/ tokens-backup/
```

### 4. Handle Disconnections
- Venom Bot will automatically try to reconnect
- Monitor the connection status via the health endpoint

## 🎉 You're All Set!

Your WhatsApp booking bot is now running on Venom Bot - completely free! 

### What's Next?
- Customize your bot messages
- Add more services and barbers
- Integrate with your existing systems
- Deploy to production

## 📞 Need Help?

If you encounter issues:
1. Check the logs first (`venom.log` and console output)
2. Verify your environment variables
3. Ensure ports are not blocked
4. Create an issue in the repository

## 🔄 Reverting to Twilio (If Needed)

If you need to go back to Twilio for any reason:
1. Restore your old `.env` file with Twilio credentials
2. Install Twilio: `pip install twilio==8.10.0`
3. Revert the webhook endpoint to `/webhook` instead of `/webhook/venom`
4. Update your Twilio webhook URL

---

**Enjoy your free WhatsApp booking bot!** 🎉 